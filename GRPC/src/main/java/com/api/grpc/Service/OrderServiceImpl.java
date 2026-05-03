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
    int orderId = Integer.parseInt(request.getOrderId());
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
                int orderId = Integer.parseInt(request.getOrderId());
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
            }

            @Override
            public void onCompleted() {
                responseObserver.onCompleted();
            }
        };

    }
}