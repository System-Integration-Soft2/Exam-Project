package com.api.websocket.Handler;

import com.api.websocket.Repository.MovieRepository;
import com.api.websocket.Repository.ReviewRepository;
import com.api.websocket.Entity.Review;
import com.api.websocket.dto.ErrorResponse;
import com.api.websocket.dto.MovieIdRequest;
import com.api.websocket.dto.ReviewResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataAccessException;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;
import org.springframework.web.util.HtmlUtils;
import tools.jackson.core.JacksonException;
import tools.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.util.List;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

@Component
public class StreamingHandler extends TextWebSocketHandler {

    private static final Logger log = LoggerFactory.getLogger(StreamingHandler.class);
    private static final long POLL_INTERVAL_MS = 2000L;

    private final ObjectMapper objectMapper;
    private final MovieRepository movieRepository;
    private final ReviewRepository reviewRepository;

    private final ConcurrentHashMap<String, SessionState> sessions = new ConcurrentHashMap<>();

    public StreamingHandler(ObjectMapper objectMapper,
                            MovieRepository movieRepository,
                            ReviewRepository reviewRepository) {
        this.objectMapper = objectMapper;
        this.movieRepository = movieRepository;
        this.reviewRepository = reviewRepository;
    }

    @Override
    public void afterConnectionEstablished(WebSocketSession session) {
        SessionState state = new SessionState();
        sessions.put(session.getId(), state);

        state.scheduler = Executors.newSingleThreadScheduledExecutor();
        state.scheduler.scheduleAtFixedRate(
                () -> pollAndPush(session, state),
                POLL_INTERVAL_MS,
                POLL_INTERVAL_MS,
                TimeUnit.MILLISECONDS
        );
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
        SessionState state = sessions.remove(session.getId());
        if (state != null && state.scheduler != null) {
            state.scheduler.shutdown();
        }
    }


    @Override
    public void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
        String payload = message.getPayload();

        MovieIdRequest request;
        try {
            request = objectMapper.readValue(payload, MovieIdRequest.class);
        } catch (JacksonException e) {
            sendError(session, "invalid_request",
                    "Malformed JSON: expected {\"movieId\": <integer>}");
            return;
        }

        Integer movieId = request.getMovieId();
        if (movieId == null || movieId <= 0) {
            sendError(session, "invalid_movie_id",
                    "movieId must be a positive integer");
            return;
        }

        try {
            if (movieRepository.findById(movieId).isEmpty()) {
                sendError(session, "movie_not_found",
                        "No movie found with id " + movieId);
                return;
            }
        } catch (DataAccessException e) {
            log.warn("DB error checking movie id={} session={}", movieId, session.getId(), e);
            sendError(session, "internal_error",
                    "A database error occurred. Please try again.");
            return;
        }

        SessionState state = sessions.get(session.getId());
        if (state == null) {
            // Session closed between connection and message — nothing to do so we return
            return;
        }

        state.subscribedMovieIds.add(movieId);

        // send all existing reviews for this movie immediately.
        List<Review> catchUp;
        try {
            catchUp = reviewRepository.findByMovieIdInAndIdGreaterThanOrderByIdAsc(
                    List.of(movieId), 0);
        } catch (DataAccessException e) {
            log.warn("DB error during catch-up for movie id={} session={}", movieId, session.getId(), e);
            sendError(session, "internal_error",
                    "A database error occurred fetching existing reviews. Please try again.");
            return;
        }

        for (Review review : catchUp) {
            String json = objectMapper.writeValueAsString(toResponse(review));
            synchronized (session) {
                session.sendMessage(new TextMessage(json));
            }
            // Update lastSeenReviewId so the polling task doesn't re-send these.
            state.lastSeenReviewId.accumulateAndGet(review.getId(), Math::max);
        }
    }


    // POLLING/subscirption logic
    private void pollAndPush(WebSocketSession session, SessionState state) {
        Set<Integer> subscribedIds = state.subscribedMovieIds;
        if (subscribedIds.isEmpty()) {
            return;
        }

        try {
            int sinceId = state.lastSeenReviewId.get();
            List<Review> newReviews =
                    reviewRepository.findByMovieIdInAndIdGreaterThanOrderByIdAsc(
                            subscribedIds, sinceId);

            for (Review review : newReviews) {
                String json = objectMapper.writeValueAsString(toResponse(review));
                synchronized (session) {
                    session.sendMessage(new TextMessage(json));
                }
                state.lastSeenReviewId.accumulateAndGet(review.getId(), Math::max);
            }

        } catch (DataAccessException | IOException e) {
            log.warn("Polling error for session={}: {}", session.getId(), e.getMessage(), e);
            try {
                String errorJson = objectMapper.writeValueAsString(
                        new ErrorResponse("internal_error",
                                "A transient error occurred. Polling will continue."));
                synchronized (session) {
                    session.sendMessage(new TextMessage(errorJson));
                }
            } catch (Exception ignored) {
                log.warn("Could not send error frame to session={}", session.getId());
            }
        }
    }

    private void sendError(WebSocketSession session, String error, String message) throws Exception {
        ErrorResponse errorResponse = new ErrorResponse(error, message);
        session.sendMessage(new TextMessage(objectMapper.writeValueAsString(errorResponse)));
    }


    // Build a ReviewResponse with HTML-escaped DB-sourced string fields.

    private static ReviewResponse toResponse(Review review) {
        String movieTitle = review.getMovie() != null
                ? HtmlUtils.htmlEscape(review.getMovie().getTitle())
                : null;
        String comment = escape(review.getComment());
        return new ReviewResponse(review, movieTitle, comment);
    }

    private static String escape(String value) {
        return value == null ? null : HtmlUtils.htmlEscape(value);
    }

    private static final class SessionState {
        final Set<Integer> subscribedMovieIds = ConcurrentHashMap.newKeySet();
        final AtomicInteger lastSeenReviewId = new AtomicInteger(0);
        volatile ScheduledExecutorService scheduler;
    }
}
