package com.gamified.chat.config;

import com.zaxxer.hikari.HikariDataSource;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;

import javax.sql.DataSource;

@Configuration
public class DataSourceConfig {

    private static final Logger log = LoggerFactory.getLogger(DataSourceConfig.class);

    @Value("${spring.datasource.url}")
    private String url;

    @Value("${spring.datasource.username:sa}")
    private String username;

    @Value("${spring.datasource.password:}")
    private String password;

    @Bean
    @Primary
    public DataSource dataSource() {
        String cleanUrl = url != null ? url.trim() : "";
        String cleanUser = username != null ? username.trim() : "";
        String cleanPass = password != null ? password.trim() : "";

        log.info("Initializing Hikari DataSource for URL: {} (User: {})", cleanUrl, cleanUser);

        HikariDataSource ds = new HikariDataSource();
        ds.setJdbcUrl(cleanUrl);
        ds.setUsername(cleanUser);
        ds.setPassword(cleanPass);

        if (cleanUrl.contains(":postgresql:")) {
            ds.setDriverClassName("org.postgresql.Driver");
        } else if (cleanUrl.contains(":h2:")) {
            ds.setDriverClassName("org.h2.Driver");
        }

        return ds;
    }
}
