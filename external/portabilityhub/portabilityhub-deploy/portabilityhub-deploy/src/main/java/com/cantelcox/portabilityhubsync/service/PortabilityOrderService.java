package com.cantelcox.portabilityhubsync.service;

import com.cantelcox.portabilityhubsync.domain.PortabilityOrderEntity;
import com.cantelcox.portabilityhubsync.domain.PortabilityOrderStatus;
import com.cantelcox.portabilityhubsync.repository.PortabilityOrderRepository;
import com.cantelcox.portabilityhubsync.web.dto.CreatePortabilityOrderRequest;
import com.cantelcox.portabilityhubsync.web.dto.NumberPortabilityOrderView;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.OffsetDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.UUID;

@Service
public class PortabilityOrderService {

    private final PortabilityOrderRepository repository;
    private final JsonPayloads json;

    public PortabilityOrderService(PortabilityOrderRepository repository, JsonPayloads json) {
        this.repository = repository;
        this.json = json;
    }

    @Transactional
    public NumberPortabilityOrderView create(CreatePortabilityOrderRequest request) {
        if (!"port-in".equalsIgnoreCase(request.requestType)) {
            throw new InvalidRequestException("Only requestType 'port-in' is supported");
        }

        OffsetDateTime now = OffsetDateTime.now();
        NumberPortabilityOrderView order = new NumberPortabilityOrderView();
        order.orderId = generateOrderId();
        order.requestType = request.requestType;
        order.number = request.number;
        order.recipientOperator = request.recipientOperator;
        order.currentOperator = request.currentOperator;
        order.customerInfo = request.customerInfo;
        order.requestedPortDate = request.requestedPortDate;
        order.status = PortabilityOrderStatus.PENDING_OUT_VALIDATION;
        order.createdAt = now;
        order.lastUpdate = now;

        repository.save(toEntity(order));
        return order;
    }

    @Transactional(readOnly = true)
    public NumberPortabilityOrderView retrieve(String orderId) {
        return repository.findById(orderId)
                .map(e -> json.fromJson(e.getPayload(), NumberPortabilityOrderView.class))
                .orElseThrow(() -> notFound(orderId));
    }

    @Transactional(readOnly = true)
    public List<NumberPortabilityOrderView> listAll() {
        return repository.findAll().stream()
                .map(e -> json.fromJson(e.getPayload(), NumberPortabilityOrderView.class))
                .toList();
    }

    @Transactional(readOnly = true)
    public List<NumberPortabilityOrderView> findByStatus(PortabilityOrderStatus status) {
        return repository.findByStatus(status).stream()
                .map(e -> json.fromJson(e.getPayload(), NumberPortabilityOrderView.class))
                .toList();
    }

    @Transactional
    public NumberPortabilityOrderView updateAfterValidation(String orderId,
                                                            PortabilityOrderStatus status,
                                                            OffsetDateTime confirmedPortDate,
                                                            String rejectionReason,
                                                            String notes) {
        PortabilityOrderEntity entity = repository.findById(orderId).orElseThrow(() -> notFound(orderId));
        NumberPortabilityOrderView order = json.fromJson(entity.getPayload(), NumberPortabilityOrderView.class);

        if (order.status != PortabilityOrderStatus.PENDING_OUT_VALIDATION) {
            throw new ConflictException(
                    "Order '" + orderId + "' is not awaiting OUT validation (current status: "
                            + order.status.getValue() + ")");
        }

        order.status = status;
        order.confirmedPortDate = confirmedPortDate;
        order.rejectionReason = rejectionReason;
        order.notes = notes;
        order.lastUpdate = OffsetDateTime.now();

        repository.save(toEntity(order));
        return order;
    }

    @Transactional
    public NumberPortabilityOrderView markPortCompleted(String orderId) {
        PortabilityOrderEntity entity = repository.findById(orderId).orElseThrow(() -> notFound(orderId));
        NumberPortabilityOrderView order = json.fromJson(entity.getPayload(), NumberPortabilityOrderView.class);

        if (order.status != PortabilityOrderStatus.APPROVED) {
            throw new ConflictException(
                    "Order '" + orderId + "' must be approved before port completion (current status: "
                            + order.status.getValue() + ")");
        }

        order.status = PortabilityOrderStatus.PORT_COMPLETED;
        order.lastUpdate = OffsetDateTime.now();
        repository.save(toEntity(order));
        return order;
    }

    @Transactional
    public void deleteAll() {
        repository.deleteAll();
    }

    private PortabilityOrderEntity toEntity(NumberPortabilityOrderView order) {
        PortabilityOrderEntity entity = new PortabilityOrderEntity();
        entity.setId(order.orderId);
        entity.setStatus(order.status);
        entity.setCreationDate(order.createdAt);
        entity.setLastUpdate(order.lastUpdate);
        entity.setPayload(json.toJson(order));
        return entity;
    }

    private static String generateOrderId() {
        String date = OffsetDateTime.now().toLocalDate().format(DateTimeFormatter.BASIC_ISO_DATE);
        String suffix = UUID.randomUUID().toString().substring(0, 6).toUpperCase();
        return "PORT-" + date + "-" + suffix;
    }

    private ResourceNotFoundException notFound(String orderId) {
        return new ResourceNotFoundException("Portability order '" + orderId + "' not found");
    }
}
