package com.cantelcox.portabilityhubsync.repository;

import com.cantelcox.portabilityhubsync.domain.PortabilityOrderEntity;
import com.cantelcox.portabilityhubsync.domain.PortabilityOrderStatus;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface PortabilityOrderRepository extends JpaRepository<PortabilityOrderEntity, String> {

    List<PortabilityOrderEntity> findByStatus(PortabilityOrderStatus status);
}
