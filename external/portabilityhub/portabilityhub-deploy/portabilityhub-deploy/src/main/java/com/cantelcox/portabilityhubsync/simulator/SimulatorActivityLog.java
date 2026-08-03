package com.cantelcox.portabilityhubsync.simulator;

import org.springframework.stereotype.Component;

import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

@Component
public class SimulatorActivityLog {

    public record ActivityEntry(
            OffsetDateTime timestamp,
            String fromParty,
            String toParty,
            String direction,
            String label,
            Object payload) {}

    private final List<ActivityEntry> entries = new CopyOnWriteArrayList<>();

    public void record(String fromParty, String toParty, String label, Object payload) {
        entries.add(new ActivityEntry(
                OffsetDateTime.now(),
                fromParty,
                toParty,
                fromParty + " → " + toParty,
                label,
                payload));
    }

    public List<ActivityEntry> list() {
        return List.copyOf(entries);
    }

    public void clear() {
        entries.clear();
    }
}
