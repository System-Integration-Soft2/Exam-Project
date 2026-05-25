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

import java.util.Optional;

@Component
public class UnaryHandler extends TextWebSocketHandler {

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Autowired
    private MovieRepository movieRepository;

    @Override
    public void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
        String payload = message.getPayload();
        System.out.println("Received message: " + payload);
        int movieId;

        // Ikke indtastet et gyldigt heltal
        try {
            movieId = Integer.parseInt(payload.trim());
        } catch (NumberFormatException e) {
            session.sendMessage(new TextMessage("Fejl i Film ID format. Vær sikker på at du sender et gyldigt heltal."));
            session.close();
            return;
        }

        Optional<Movie> movie = movieRepository.findById(movieId);

        // Film ikke fundet
        if (movie.isEmpty()) {
            session.sendMessage(new TextMessage("Filmen med id" + movieId + " blev ikke fundet"));
            session.close();
            return;
        }

        MovieUpdate response = new MovieUpdate(
                movie.get().getId(),
                movie.get().getTitle(),
                movie.get().getReleaseYear(),
                movie.get().getDirector(),
                movie.get().getStatus()
        );

        String json = objectMapper.writeValueAsString(response);
        session.sendMessage(new TextMessage(json));
        
    }
}
