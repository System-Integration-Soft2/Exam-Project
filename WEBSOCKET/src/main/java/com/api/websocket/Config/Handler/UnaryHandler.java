package com.api.websocket.Config.Handler;

import org.springframework.stereotype.Component;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;

@Component
public class UnaryHandler extends TextWebSocketHandler {


    @Override
    public void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
        String payload = message.getPayload();
        System.out.println("Received message: " + payload);

        // Simulate processing the message and generating a response
        String response = "Status på ordrer: UNDER_LEVERING " + payload;

        // Send the response back to the client
        session.sendMessage(new TextMessage(response));
        session.close();
    }
}
