package com.api.websocket.Entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@NoArgsConstructor
@Entity
@Table(name = "reviews")
public class Review {

    @Id
    private Integer id;

    @Column(name = "movie_id")
    private Integer movieId;

    @Column(name = "user_id")
    private Integer userId;

    private Integer rating;

    private String comment;

    @Column(name = "created_at")
    private String createdAt;

    @ManyToOne(fetch = FetchType.EAGER)
    @JoinColumn(name = "movie_id", insertable = false, updatable = false)
    private Movie movie;
}
