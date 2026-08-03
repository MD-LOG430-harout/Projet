package com.cantelcox.portabilityhubsync.simulator;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
@ConditionalOnProperty(name = "portabilityhubsync.simulator.enabled", havingValue = "true")
public class SimulatorPageController {

    @GetMapping({"/simulator", "/simulator/"})
    public String redirectToSimulator() {
        return "redirect:/simulator/index.html";
    }

    @GetMapping("/")
    public String redirectRootToSimulator() {
        return "redirect:/simulator/index.html";
    }
}
