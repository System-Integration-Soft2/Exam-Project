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
public class StreamingHandler extends TextWebSocketHandler {

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Autowired
    private OrderRepository orderRepository;

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
        String payload = message.getPayload();
        int orderId = Integer.parseInt(payload.trim());

        Optional<Order> optionalOrder = orderRepository.findById(orderId);

        if (optionalOrder.isEmpty()) {
            session.sendMessage(new TextMessage("Ordre ikke fundet"));
            session.close();
            return;
        }

        String[][] updates = {
                {"PREPARING", "Restauranten er ved at forberede din mad..."},
                {"PICKED_UP", "Din mad er klar og rider er på vej!"},
                {"DELIVERING", "Rideren er 500m væk"},
                {"DELIVERING", "Rideren er 200m væk"},
                {"DELIVERED", "LEVERET! God appetit 🍕"}
        };

        Order order = optionalOrder.get();

        for (String[] update: updates) {
            // Opdater status i databasen
            order.setStatus(update[0]);
            order.setMessage(update[1]);
            orderRepository.save(order);


            // Send opdateringer til klienten
            OrderUpdate response = new OrderUpdate(orderId, order.getStatus(), order.getMessage());
            String jsonResponse = objectMapper.writeValueAsString(response);
            session.sendMessage(new TextMessage(jsonResponse));

            Thread.sleep(2000);
        }

        session.close();
    }
}
