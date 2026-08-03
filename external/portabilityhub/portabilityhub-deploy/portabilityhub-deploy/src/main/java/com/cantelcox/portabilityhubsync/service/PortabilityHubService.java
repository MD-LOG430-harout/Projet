package com.cantelcox.portabilityhubsync.service;

import com.cantelcox.portabilityhubsync.domain.PortabilityOrderStatus;
import com.cantelcox.portabilityhubsync.web.dto.CreatePortabilityOrderRequest;
import com.cantelcox.portabilityhubsync.web.dto.CreatePortabilityOrderResponse;
import com.cantelcox.portabilityhubsync.web.dto.NumberPortabilityOrderView;
import com.cantelcox.portabilityhubsync.web.dto.ValidateOutRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.OffsetDateTime;
import java.util.List;

@Service
public class PortabilityHubService {

    private static final Logger log = LoggerFactory.getLogger(PortabilityHubService.class);

    private final PortabilityOrderService orderService;
    private final WebhookService webhookService;

    public PortabilityHubService(PortabilityOrderService orderService, WebhookService webhookService) {
        this.orderService = orderService;
        this.webhookService = webhookService;
    }

    @Transactional
    public CreatePortabilityOrderResponse createPortIn(CreatePortabilityOrderRequest request) {
        NumberPortabilityOrderView order = orderService.create(request);
        webhookService.notifyOutValidationNeeded(order);
        log.info("Created portability order {} awaiting OUT validation", order.orderId);
        return new CreatePortabilityOrderResponse(order.orderId, order.status, order.createdAt);
    }

    @Transactional(readOnly = true)
    public NumberPortabilityOrderView getOrder(String orderId) {
        return orderService.retrieve(orderId);
    }

    @Transactional(readOnly = true)
    public List<NumberPortabilityOrderView> listOrders(String statusFilter) {
        if (statusFilter == null || statusFilter.isBlank()) {
            return orderService.listAll();
        }
        return orderService.findByStatus(PortabilityOrderStatus.fromValue(statusFilter.trim()));
    }

    @Transactional
    public NumberPortabilityOrderView validateOut(String orderId, ValidateOutRequest request) {
        String normalizedStatus = request.status == null ? "" : request.status.trim().toLowerCase();
        PortabilityOrderStatus newStatus = switch (normalizedStatus) {
            case "approved" -> PortabilityOrderStatus.APPROVED;
            case "rejected" -> PortabilityOrderStatus.REJECTED;
            default -> throw new InvalidRequestException("status must be 'approved' or 'rejected'");
        };

        if (newStatus == PortabilityOrderStatus.APPROVED && request.confirmedPortDate == null) {
            throw new InvalidRequestException("confirmedPortDate is required when status is approved");
        }
        if (newStatus == PortabilityOrderStatus.REJECTED
                && (request.rejectionReason == null || request.rejectionReason.isBlank())) {
            throw new InvalidRequestException("rejectionReason is required when status is rejected");
        }

        NumberPortabilityOrderView order = orderService.updateAfterValidation(
                orderId,
                newStatus,
                request.confirmedPortDate,
                request.rejectionReason,
                request.notes);

        if (newStatus == PortabilityOrderStatus.APPROVED) {
            webhookService.notifyOrderApproved(order);
            if (!request.confirmedPortDate.isAfter(OffsetDateTime.now())) {
                completePort(orderId);
                return orderService.retrieve(orderId);
            }
        } else {
            webhookService.notifyOrderRejected(order);
        }

        return order;
    }

    @Transactional
    public int completeDuePorts() {
        List<NumberPortabilityOrderView> approved = orderService.findByStatus(PortabilityOrderStatus.APPROVED);
        OffsetDateTime now = OffsetDateTime.now();
        int completed = 0;

        for (NumberPortabilityOrderView order : approved) {
            if (order.confirmedPortDate != null && !order.confirmedPortDate.isAfter(now)) {
                completePort(order.orderId);
                completed++;
            }
        }
        return completed;
    }

    private void completePort(String orderId) {
        NumberPortabilityOrderView completed = orderService.markPortCompleted(orderId);
        webhookService.notifyPortCompleted(completed);
        log.info("Portability order {} completed", orderId);
    }
}
