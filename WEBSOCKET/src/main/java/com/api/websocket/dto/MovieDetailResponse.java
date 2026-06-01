package com.api.websocket.dto;

import com.api.websocket.Entity.Movie;
import lombok.Getter;
import org.springframework.web.util.HtmlUtils;

import java.util.List;
import java.util.stream.Collectors;

@Getter
public class MovieDetailResponse {

    private final Integer id;
    private final String title;
    private final Integer releaseYear;
    private final Integer runtimeMinutes;
    private final String director;
    private final String synopsis;
    private final List<String> genres;

    public MovieDetailResponse(Movie movie) {
        this.id = movie.getId();
        this.title = escape(movie.getTitle());
        this.releaseYear = movie.getReleaseYear();
        this.runtimeMinutes = movie.getRuntimeMinutes();
        this.director = escape(movie.getDirector());
        this.synopsis = escape(movie.getSynopsis());
        this.genres = movie.getGenres() == null
                ? List.of()
                : movie.getGenres().stream()
                        .map(g -> escape(g.getName()))
                        .collect(Collectors.toList());
    }

    private static String escape(String value) {
        return value == null ? null : HtmlUtils.htmlEscape(value);
    }
}
