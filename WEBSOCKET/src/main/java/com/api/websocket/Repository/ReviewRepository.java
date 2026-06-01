package com.api.websocket.Repository;

import com.api.websocket.Entity.Review;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Collection;
import java.util.List;

@Repository
public interface ReviewRepository extends JpaRepository<Review, Integer> {

    List<Review> findByMovieIdInAndIdGreaterThanOrderByIdAsc(
            Collection<Integer> movieIds, Integer sinceId);
}
