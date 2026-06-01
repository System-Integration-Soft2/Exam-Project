package com.api.websocket.dto;

import com.api.websocket.Entity.Review;
import lombok.Getter;

@Getter
public class ReviewResponse {

    private final Integer reviewId;
    private final Integer movieId;
    private final String movieTitle;
    private final Integer rating;
    private final String comment;
    private final String createdAt;

    public ReviewResponse(Review review, String escapedMovieTitle, String escapedComment) {
        this.reviewId = review.getId();
        this.movieId = review.getMovieId();
        this.movieTitle = escapedMovieTitle;
        this.rating = review.getRating();
        this.comment = escapedComment;
        this.createdAt = review.getCreatedAt();
    }
}
