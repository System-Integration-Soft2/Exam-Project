package com.api.websocket.Handler;

import com.api.websocket.Entity.Movie;
import com.api.websocket.Repository.MovieRepository;
import com.api.websocket.dto.MovieUpdate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;
import tools.jackson.databind.ObjectMapper;

import java.util.List;
import java.util.Optional;

@Component
public class StreamingHandler extends TextWebSocketHandler {

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Autowired
    private MovieRepository movieRepository;

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
        String payload = message.getPayload();
        int movieId;

        // Ikke indtastet et gyldigt heltal
        try{
            movieId = Integer.parseInt(payload.trim());
        } catch (NumberFormatException e) {
            session.sendMessage(new TextMessage("Fejl i Film ID format. Vær sikker på at du sender et gyldigt heltal."));
            return;
        }

        Optional<Movie> movieOrder = movieRepository.findById(movieId);

        // Film ikke fundet
        if (movieOrder.isEmpty()) {
            session.sendMessage(new TextMessage("Film med id " + movieId + " blev ikke fundet"));
            return;
        }


        // Simulerer opdateringer ved at sende den aktuelle status for ordren og derefter sende opdateringer hver 2. sekund
        List<Movie> movies = movieRepository.findAll();

        for (Movie movie : movies) {
            MovieUpdate response = new MovieUpdate(
                    movie.getId(),
                    movie.getTitle(),
                    movie.getReleaseYear(),
                    movie.getRuntimeMinutes(),
                    movie.getDirector(),
                    movie.getSynopsis()
            );
            String json = objectMapper.writeValueAsString(response);
            session.sendMessage(new TextMessage(json));
            Thread.sleep(2000);
        }
    }
}
