package com.api.grpc.Service;

import com.api.grpc.Repository.OrderRepository;
import com.api.grpc.Security.SecurityUtils;
import net.devh.boot.grpc.server.service.GrpcService;
import io.grpc.stub.StreamObserver;
import order.OrderServiceGrpc;

@GrpcService
public class OrderServiceImpl extends OrderServiceGrpc.OrderServiceImplBase {

    private final OrderRepository orderRepository;

    public OrderServiceImpl(OrderRepository orderRepository) {
        this.orderRepository = orderRepository;
    }

    @Override
    public void getOrderStatus(order.GetOrderStatusRequest request, StreamObserver<order.GetOrderStatusResponse> responseObserver) {
        String orderIdStr = request.getOrderId();

        // Valider at order_id ikke er tom eller null
        if (orderIdStr == null || orderIdStr.isBlank()) {
            responseObserver.onError(
                    io.grpc.Status.INVALID_ARGUMENT
                            .withDescription("Order ID cannot be empty")
                            .asRuntimeException()
            );
            return;
        }

        // Valider at order_id er et gyldigt tal
        int orderId;
        try {
            orderId = Integer.parseInt(orderIdStr);
        } catch (NumberFormatException e) {
            responseObserver.onError(
                    io.grpc.Status.INVALID_ARGUMENT
                            .withDescription("Order ID must be a valid number")
                            .asRuntimeException()
            );
            return;
        }

        var foundOrder = orderRepository.findById(orderId);

        if (foundOrder.isEmpty()) {
            responseObserver.onError(
                    io.grpc.Status.NOT_FOUND
                            .withDescription("Order not found")
                            .asRuntimeException()
            );
            return;
        }


        var orders = foundOrder.get();

        order.GetOrderStatusResponse response = order.GetOrderStatusResponse.newBuilder()
                .setOrderId(String.valueOf(orders.getOrderId()))
                .setOrderStatus(SecurityUtils.sanitize(orders.getStatus()))
                .setMessage(SecurityUtils.sanitize(orders.getMessage()))
                .build();

        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public StreamObserver<TrackOrderRequest> trackOrder(
            StreamObserver<TrackOrderResponse> responseObserver) {

        return new StreamObserver<TrackOrderRequest>() {

            @Override
            public void onNext(TrackOrderRequest request) {
                int orderId = Integer.parseInt(request.getOrderId());

                // Start polling i en separat tråd
                new Thread(() -> {
                    String lastStatus = "";

                    try {
                        while (true) {
                            var foundOrder = orderRepository.findById(orderId);

                            if (foundOrder.isEmpty()) {
                                responseObserver.onError(
                                        io.grpc.Status.NOT_FOUND
                                                .withDescription("Order not found")
                                                .asRuntimeException()
                                );
                                return;
                            }

                            var orders = foundOrder.get();
                            String currentStatus = orders.getStatus();

                            // Send kun opdatering hvis status har ændret sig
                            if (!currentStatus.equals(lastStatus)) {
                                TrackOrderResponse response = TrackOrderResponse.newBuilder()
                                        .setOrderId(String.valueOf(orders.getOrderId()))
                                        .setLocation(SecurityUtils.sanitize(orders.getLocation()))
                                        .setStatus(SecurityUtils.sanitize(orders.getStatus()))
                                        .build();

                                responseObserver.onNext(response);
                                lastStatus = currentStatus;
                            }

                            // Stop hvis ordren er leveret
                            if (currentStatus.equals("DELIVERED")) {
                                responseObserver.onCompleted();
                                return;
                            }

                            Thread.sleep(2000); // Poll hvert 2. sekund
                        }
                    } catch (InterruptedException e) {
                        Thread.currentThread().interrupt();
                    } catch (Exception e) {
                        responseObserver.onError(e);
                    }
                }).start();
            }

            @Override
            public void onError(Throwable t) {
                System.err.println("Client error: " + t.getMessage());
            }

            @Override
            public void onCompleted() {
                responseObserver.onCompleted();
            }
        };
    }

    }
}