package com.cantelcox.portabilityhubsync.simulator;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
import org.springframework.web.util.ContentCachingRequestWrapper;
import org.springframework.web.util.ContentCachingResponseWrapper;

import java.io.IOException;
import java.nio.charset.StandardCharsets;

@Component
@Order(Ordered.LOWEST_PRECEDENCE - 10)
@ConditionalOnProperty(name = "portabilityhubsync.simulator.enabled", havingValue = "true")
public class SimulatorRestActivityFilter extends OncePerRequestFilter {

    private static final String PARTY_HEADER = "X-Simulator-Party";

    private final SimulatorActivityLog activityLog;

    public SimulatorRestActivityFilter(SimulatorActivityLog activityLog) {
        this.activityLog = activityLog;
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        String path = request.getRequestURI();
        return !path.startsWith("/portability/");
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                      HttpServletResponse response,
                                      FilterChain filterChain) throws ServletException, IOException {
        ContentCachingRequestWrapper wrappedRequest = new ContentCachingRequestWrapper(request);
        ContentCachingResponseWrapper wrappedResponse = new ContentCachingResponseWrapper(response);

        filterChain.doFilter(wrappedRequest, wrappedResponse);

        String party = request.getHeader(PARTY_HEADER);
        if (party == null || party.isBlank()) {
            wrappedResponse.copyBodyToResponse();
            return;
        }

        String method = request.getMethod();
        String path = request.getRequestURI();
        String label = method + " " + path + " (via Hub Gateway)";
        Object payload = readJsonBody(wrappedRequest);

        activityLog.record(party.toUpperCase(), "HUB", label, payload);

        if (wrappedResponse.getStatus() >= 200 && wrappedResponse.getStatus() < 300) {
            String responseLabel = responseLabel(path, wrappedResponse.getStatus());
            Object responseBody = readJsonBody(wrappedResponse);
            activityLog.record("HUB", party.toUpperCase(), responseLabel, responseBody);
        }

        wrappedResponse.copyBodyToResponse();
    }

    private static String responseLabel(String path, int status) {
        if (path.contains("/validate-out")) {
            return status + " Updated · validate-out";
        }
        if (path.endsWith("/portability/order") || path.endsWith("/order")) {
            return status + " Created · port-in";
        }
        if (path.contains("/portability/hub")) {
            return status + " Hub subscription";
        }
        if (path.contains("/portability/order/")) {
            return status + " Order status";
        }
        return status + " OK";
    }

    private static Object readJsonBody(ContentCachingRequestWrapper request) {
        byte[] content = request.getContentAsByteArray();
        if (content.length == 0) {
            return null;
        }
        return new String(content, StandardCharsets.UTF_8);
    }

    private static Object readJsonBody(ContentCachingResponseWrapper response) {
        byte[] content = response.getContentAsByteArray();
        if (content.length == 0) {
            return null;
        }
        return new String(content, StandardCharsets.UTF_8);
    }
}
