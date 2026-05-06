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

import java.util.List;
import java.util.Optional;

@Component
public class StreamingHandler extends TextWebSocketHandler {

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Autowired
    private OrderRepository orderRepository;

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
        String payload = message.getPayload();
        int orderId;

        // Ikke indtastet et gyldigt heltal
        try{
            orderId = Integer.parseInt(payload.trim());
        } catch (NumberFormatException e) {
            session.sendMessage(new TextMessage("Fejl i ordre ID format. Vær sikker på at du sender et gyldigt heltal."));
            session.close();
            return;
        }

        Optional<Order> optionalOrder = orderRepository.findById(orderId);

        // Order ikke fundet
        if (optionalOrder.isEmpty()) {
            session.sendMessage(new TextMessage("Ordre med id" + orderId + "blev ikke fundet"));
            session.close();
            return;
        }



        Order order = optionalOrder.get();

        // Hvis ordren allerede er leveret, send en besked og luk forbindelsen
        if (order.getStatus().equals("DELIVERED")) {
            session.sendMessage(new TextMessage("Ordre er allerede leveret. Ingen yderligere opdateringer."));
            session.close();
            return;
        }

        // Simulerer opdateringer ved at sende den aktuelle status for ordren og derefter sende opdateringer hver 2. sekund
        List<Order> orders = orderRepository.findAll();

        for (Order currentOrder : orders) {
            OrderUpdate response = new OrderUpdate(
                    currentOrder.getId(),
                    currentOrder.getStatus(),
                    currentOrder.getMessage()
            );
            String jsonResponse = objectMapper.writeValueAsString(response);
            session.sendMessage(new TextMessage(jsonResponse));
            Thread.sleep(2000);
        }

        session.close();
    }
}
