package uk.co.willanthony.rifflebackend;

import org.springframework.boot.SpringApplication;

public class TestRiffleBackendApplication {

    public static void main(String[] args) {
        SpringApplication.from(RiffleBackendApplication::main).with(TestcontainersConfiguration.class).run(args);
    }

}
