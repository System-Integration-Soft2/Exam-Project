package com.api.websocket.dto;

import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@AllArgsConstructor
public class MovieUpdate {
    private int id;
    private String title;
    private int releaseYear;
    private String director;
    private String status;
}
