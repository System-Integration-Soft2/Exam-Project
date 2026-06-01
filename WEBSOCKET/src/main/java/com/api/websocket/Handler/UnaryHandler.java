package com.api.websocket.Handler;

import com.api.websocket.Entity.Movie;
import com.api.websocket.Repository.MovieRepository;
import com.api.websocket.dto.ErrorResponse;
import com.api.websocket.dto.MovieDetailResponse;
import com.api.websocket.dto.MovieIdRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataAccessException;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;
import tools.jackson.core.JacksonException;
import tools.jackson.databind.ObjectMapper;

import java.util.Optional;

@Component
public class UnaryHandler extends TextWebSocketHandler {

    private static final Logger log = LoggerFactory.getLogger(UnaryHandler.class);

    private final ObjectMapper objectMapper;
    private final MovieRepository movieRepository;

    public UnaryHandler(ObjectMapper objectMapper, MovieRepository movieRepository) {
        this.objectMapper = objectMapper;
        this.movieRepository = movieRepository;
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

        Optional<Movie> movieOpt;
        try {
            movieOpt = movieRepository.findById(movieId);
        } catch (DataAccessException e) {
            log.warn("DB error fetching movie id={} session={}", movieId, session.getId(), e);
            sendError(session, "internal_error",
                    "A database error occurred. Please try again.");
            return;
        }

        if (movieOpt.isEmpty()) {
            sendError(session, "movie_not_found",
                    "No movie found with id " + movieId);
            return;
        }

        MovieDetailResponse response = new MovieDetailResponse(movieOpt.get());
        String json = objectMapper.writeValueAsString(response);
        session.sendMessage(new TextMessage(json));
    }

    private void sendError(WebSocketSession session, String error, String message) throws Exception {
        ErrorResponse errorResponse = new ErrorResponse(error, message);
        session.sendMessage(new TextMessage(objectMapper.writeValueAsString(errorResponse)));
    }
}
