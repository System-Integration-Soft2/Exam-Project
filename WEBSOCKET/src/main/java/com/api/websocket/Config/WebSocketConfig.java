package com.api.websocket.Config;

import com.api.websocket.Handler.StreamingHandler;
import com.api.websocket.Handler.UnaryHandler;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;

@Configuration
@EnableWebSocket
public class WebSocketConfig implements WebSocketConfigurer {

    @Autowired
    private UnaryHandler unaryHandler;

    @Autowired
    private StreamingHandler streamingHandler;

    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {

        registry.addHandler(unaryHandler, "/ws/movies/detail")
                        .setAllowedOriginPatterns("http://localhost:3000");

        registry.addHandler(streamingHandler, "/ws/movies/reviews/stream")
                .setAllowedOriginPatterns("http://localhost:3000");

    }
}
