package com.api.grpc.Service;

import com.api.grpc.Repository.OrderRepository;
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
                .setOrderStatus(orders.getStatus())
                .setMessage(orders.getMessage())
                .build();

        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public StreamObserver<order.TrackOrderRequest> trackOrder(StreamObserver<order.TrackOrderResponse> responseObserver) {
        return new StreamObserver<order.TrackOrderRequest>() {
            @Override
            public void onNext(order.TrackOrderRequest request) {
                String orderIdStr1 = request.getOrderId();

                // Valider at order_id ikke er tom eller null
                if (orderIdStr1 == null || orderIdStr1.isBlank()) {
                    responseObserver.onError(
                            io.grpc.Status.INVALID_ARGUMENT
                                    .withDescription("Order ID cannot be empty")
                                    .asRuntimeException()
                    );
                    return;
                }

                // Valider at order_id er et gyldigt tal
                int orderId1;
                try {
                    orderId1 = Integer.parseInt(orderIdStr1);
                } catch (NumberFormatException e) {
                    responseObserver.onError(
                            io.grpc.Status.INVALID_ARGUMENT
                                    .withDescription("Order ID must be a valid number")
                                    .asRuntimeException()
                    );
                    return;
                }



                var foundOrder = orderRepository.findById(orderId1);

                // Valider at ordren findes

                if (foundOrder.isEmpty()) {
                    responseObserver.onError(
                            io.grpc.Status.NOT_FOUND
                                    .withDescription("Order not found")
                                    .asRuntimeException()
                    );
                    return;
                }

                var orders = foundOrder.get();

                order.TrackOrderResponse response = order.TrackOrderResponse.newBuilder()
                        .setOrderId(String.valueOf(orders.getOrderId()))
                        .setOrderStatus(orders.getStatus())
                        .setLocation(orders.getLocation())
                        .build();

                responseObserver.onNext(response);
            }

            @Override
            public void onError(Throwable t) {
                System.out.println("Client error: " + t.getMessage());
                responseObserver.onError(t);
            }

            @Override
            public void onCompleted() {
                responseObserver.onCompleted();
            }
        };

    }
}