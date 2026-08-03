package com.cantelcox.portabilityhubgateway.dev;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/gateway/dev")
@ConditionalOnProperty(name = "portabilityhubgateway.dev-token-enabled", havingValue = "true")
public class DevTokenController {

    private final JwtDevTokenService tokenService;

    public DevTokenController(JwtDevTokenService tokenService) {
        this.tokenService = tokenService;
    }

    @GetMapping("/token")
    public JwtDevTokenService.DevTokenResponse token(
            @RequestParam(defaultValue = "BSS1") String operator) {
        return tokenService.issueToken(operator);
    }
}
