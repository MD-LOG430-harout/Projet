package com.cantelcox.portabilityhubsync.web;

import com.cantelcox.portabilityhubsync.service.HubService;
import com.cantelcox.portabilityhubsync.web.dto.Hub;
import com.cantelcox.portabilityhubsync.web.dto.HubCreate;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** TMF Hub event subscription endpoints. */
@RestController
@RequestMapping("/portability/hub")
public class HubController {

    private final HubService service;

    public HubController(HubService service) {
        this.service = service;
    }

    @PostMapping
    public ResponseEntity<Hub> create(@Valid @RequestBody HubCreate request) {
        Hub created = service.create(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(created);
    }

    @GetMapping("/{id}")
    public Hub retrieve(@PathVariable String id) {
        return service.retrieve(id);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable String id) {
        service.delete(id);
        return ResponseEntity.noContent().build();
    }
}
