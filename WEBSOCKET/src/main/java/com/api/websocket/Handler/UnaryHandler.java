package com.api.websocket.Handler;

import com.api.websocket.Entity.Order;
import com.api.websocket.Repository.OrderRepository;
import com.api.websocket.dto.OrderUpdate;
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
    private OrderRepository orderRepository;

    @Override
    public void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
        String payload = message.getPayload();
        System.out.println("Received message: " + payload);
        int orderId;

        // Ikke indtastet et gyldigt heltal
        try{
            orderId = Integer.parseInt(payload.trim());
        } catch (NumberFormatException e) {
            session.sendMessage(new TextMessage("Fejl i ordre ID format. Vær sikker på at du sender et gyldigt heltal."));
            session.close();
            return;
        }

        Optional<Order> order = orderRepository.findById(orderId);

        // Order ikke fundet
        if (order.isEmpty()) {
            session.sendMessage(new TextMessage("Ordre med id" + orderId + " blev ikke fundet"));
            session.close();
            return;
        }

        if (order.isPresent()) {
            OrderUpdate response = new OrderUpdate(orderId, order.get().getStatus(), order.get().getMessage());
            String jsonResponse = objectMapper.writeValueAsString(response);
            session.sendMessage(new TextMessage(jsonResponse));
        } else {
            session.sendMessage(new TextMessage("Ordre ikke fundet"));
        }

        session.close();
    }
}
