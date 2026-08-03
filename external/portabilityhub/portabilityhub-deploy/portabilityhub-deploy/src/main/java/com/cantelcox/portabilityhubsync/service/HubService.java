package com.cantelcox.portabilityhubsync.service;

import com.cantelcox.portabilityhubsync.domain.HubEntity;
import com.cantelcox.portabilityhubsync.repository.HubRepository;
import com.cantelcox.portabilityhubsync.web.dto.Hub;
import com.cantelcox.portabilityhubsync.web.dto.HubCreate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;

@Service
public class HubService {

    private static final String BASE_HREF = "/portability/hub/";

    private final HubRepository repository;

    public HubService(HubRepository repository) {
        this.repository = repository;
    }

    @Transactional
    public Hub create(HubCreate request) {
        HubEntity entity = new HubEntity();
        entity.setId(UUID.randomUUID().toString());
        entity.setCallback(request.callback);
        entity.setQuery(request.query);
        repository.save(entity);
        return toDto(entity);
    }

    @Transactional(readOnly = true)
    public Hub retrieve(String id) {
        return repository.findById(id)
                .map(this::toDto)
                .orElseThrow(() -> new ResourceNotFoundException("Hub '" + id + "' not found"));
    }

    @Transactional
    public void delete(String id) {
        if (!repository.existsById(id)) {
            throw new ResourceNotFoundException("Hub '" + id + "' not found");
        }
        repository.deleteById(id);
    }

    @Transactional(readOnly = true)
    public List<String> listCallbacks() {
        return repository.findAll().stream()
                .map(HubEntity::getCallback)
                .toList();
    }

    @Transactional
    public void deleteAll() {
        repository.deleteAll();
    }

    private Hub toDto(HubEntity entity) {
        Hub hub = new Hub();
        hub.id = entity.getId();
        hub.href = BASE_HREF + entity.getId();
        hub.callback = entity.getCallback();
        hub.query = entity.getQuery();
        return hub;
    }
}
