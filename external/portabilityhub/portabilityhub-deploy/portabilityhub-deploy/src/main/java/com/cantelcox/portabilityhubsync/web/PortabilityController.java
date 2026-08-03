package com.cantelcox.portabilityhubsync.web;

import com.cantelcox.portabilityhubsync.service.PortabilityHubService;
import com.cantelcox.portabilityhubsync.web.dto.CreatePortabilityOrderRequest;
import com.cantelcox.portabilityhubsync.web.dto.CreatePortabilityOrderResponse;
import com.cantelcox.portabilityhubsync.web.dto.NumberPortabilityOrderView;
import com.cantelcox.portabilityhubsync.web.dto.ValidateOutRequest;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/portability/order")
public class PortabilityController {

    private final PortabilityHubService hubService;

    public PortabilityController(PortabilityHubService hubService) {
        this.hubService = hubService;
    }

    @GetMapping
    public List<NumberPortabilityOrderView> listOrders(
            @RequestParam(required = false) String status) {
        return hubService.listOrders(status);
    }

    @PostMapping
    public ResponseEntity<CreatePortabilityOrderResponse> create(
            @Valid @RequestBody CreatePortabilityOrderRequest request) {
        CreatePortabilityOrderResponse response = hubService.createPortIn(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    @PostMapping("/{orderId}/validate-out")
    public NumberPortabilityOrderView validateOut(@PathVariable String orderId,
                                                 @Valid @RequestBody ValidateOutRequest request) {
        return hubService.validateOut(orderId, request);
    }

    @GetMapping("/{orderId}")
    public NumberPortabilityOrderView getOrder(@PathVariable String orderId) {
        return hubService.getOrder(orderId);
    }
}
