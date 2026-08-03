package com.cantelcox.portabilityhubsync.event;

import com.cantelcox.portabilityhubsync.domain.PortabilityOrderStatus;
import com.cantelcox.portabilityhubsync.web.dto.CustomerInfo;
import com.cantelcox.portabilityhubsync.web.dto.NumberPortabilityOrderView;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.OffsetDateTime;

/** Portability order snapshot embedded in TMF Event payloads. */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class PortabilityOrderEventRef {

    @JsonProperty("@type")
    public String atType = "PortabilityOrderRef";

    @JsonProperty("@referredType")
    public String referredType = "PortabilityOrder";

    public String id;
    public String href;
    public String number;
    public String status;
    public String recipientOperator;
    public String currentOperator;
    public OffsetDateTime requestedPortDate;
    public OffsetDateTime confirmedPortDate;
    public String rejectionReason;
    public String customerName;
    public String accountId;

    public CustomerInfo toCustomerInfo() {
        if ((customerName == null || customerName.isBlank())
                && (accountId == null || accountId.isBlank())) {
            return null;
        }
        CustomerInfo info = new CustomerInfo();
        info.name = customerName;
        info.accountId = accountId;
        return info;
    }

    public void applyCustomerInfo(CustomerInfo customerInfo) {
        if (customerInfo == null) {
            customerName = null;
            accountId = null;
            return;
        }
        customerName = customerInfo.name;
        accountId = customerInfo.accountId;
    }

    public NumberPortabilityOrderView toOrderView() {
        NumberPortabilityOrderView view = new NumberPortabilityOrderView();
        view.orderId = id;
        view.number = number;
        view.recipientOperator = recipientOperator;
        view.currentOperator = currentOperator;
        view.requestedPortDate = requestedPortDate;
        view.confirmedPortDate = confirmedPortDate;
        view.rejectionReason = rejectionReason;
        view.customerInfo = toCustomerInfo();
        if (status != null && !status.isBlank()) {
            view.status = PortabilityOrderStatus.fromValue(status);
        }
        return view;
    }
}
