package com.gamified.chat.controller;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;

@Controller
public class WebViewController {

    @GetMapping("/")
    public String index(
            @RequestParam(required = false, defaultValue = "") String username,
            Model model) {
        model.addAttribute("initialUser", username);
        return "index";
    }

    @GetMapping("/login")
    public String loginPage() {
        return "login";
    }
}
