package com.innative.senlis;

import java.util.Arrays;
import java.util.List;

public final class Perfume {
    public final String brand;
    public final String name;
    public final String gender;
    public final String concentration;
    public final String family;
    public final String mood;
    public final String occasion;
    public final String season;
    public final int priceTier;
    public final double rating;
    public final List<String> notes;
    public final String description;

    public Perfume(
            String brand,
            String name,
            String gender,
            String concentration,
            String family,
            String mood,
            String occasion,
            String season,
            int priceTier,
            double rating,
            String[] notes,
            String description
    ) {
        this.brand = brand;
        this.name = name;
        this.gender = gender;
        this.concentration = concentration;
        this.family = family;
        this.mood = mood;
        this.occasion = occasion;
        this.season = season;
        this.priceTier = priceTier;
        this.rating = rating;
        this.notes = Arrays.asList(notes);
        this.description = description;
    }

    public String key() {
        return brand + "|" + name;
    }

    public String subtitle() {
        return gender + " • " + concentration + " • " + family;
    }
}
