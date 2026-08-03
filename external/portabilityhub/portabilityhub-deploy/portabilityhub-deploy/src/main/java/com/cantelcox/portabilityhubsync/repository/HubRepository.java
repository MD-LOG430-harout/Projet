package com.cantelcox.portabilityhubsync.repository;

import com.cantelcox.portabilityhubsync.domain.HubEntity;
import org.springframework.data.jpa.repository.JpaRepository;

public interface HubRepository extends JpaRepository<HubEntity, String> {
}
