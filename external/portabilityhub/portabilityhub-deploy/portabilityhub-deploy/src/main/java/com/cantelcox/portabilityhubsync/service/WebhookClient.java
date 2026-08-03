package com.cantelcox.portabilityhubsync.service;

/** Delivers portability webhook events to BSS callback URLs. */
public interface WebhookClient {

    void deliver(String callbackUrl, Object event);
}
