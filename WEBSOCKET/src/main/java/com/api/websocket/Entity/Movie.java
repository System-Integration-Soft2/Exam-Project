package com.api.websocket.Entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;


@Getter
@Setter
@Entity
@Table(name = "movies")
public class Movie {
    @Id
    private Integer id;
    private String title;
    @Column(name = "release_year")
    private Integer releaseYear;

    @Column(name = "runtime_minutes")
    private Integer runtimeMinutes;
    private String director;
    private String synopsis;
    
}
