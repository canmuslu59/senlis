# SENLIS Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a native Android preview of SENLIS's visual identity and personal fragrance discovery loop.

**Architecture:** A single Android module uses native Views, an isolated pure-Java match engine and local preferences. Seed fragrance records are explicitly editorial examples. The network catalogue and community are later service boundaries described in the spec.

**Tech Stack:** Java 17, Android Gradle Plugin 8.7.3, Gradle 8.11.1, Android SDK 35, JUnit 4, Windows self-hosted GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-27-senlis-design.md`

## Global Constraints

- Keep `main` untouched while building on `feature/senlis-premium-foundation`.
- Use `com.innative.senlis.preview` for the installable preview and clearly label example catalogue entries.
- Never invent prices, public comments, aggregate ratings, news or retailer availability.
- Dark editorial interface, warm gold, serif headings and original photography.

## Review Focus

- Empty profile: score reports insufficient evidence; it never says 100%.
- Avoided note: a known excluded note prevents a recommendation.
- Unknown price: it never contributes the budget points.
- Saved preferences: relaunch retains choices and favourites.
- Previous SENLIS app: the preview package installs separately regardless of signing key.

---

### Task 1: Pure match model and tests

**Files:** `app/src/main/java/com/innative/senlis/MatchEngine.java`, `app/src/test/java/com/innative/senlis/MatchEngineTest.java`.

**Interfaces:** `MatchEngine.score(Profile, Fragrance): Result`, where `Result.percent` is nullable and `Result.reasons` explains known contributions.

- [ ] Write tests for empty profile, overlapping notes, hard-excluded notes and unknown price.
- [ ] Run `javac` and the local model harness or Gradle JUnit; confirm the pre-implementation failure.
- [ ] Implement the minimal model and scoring function.
- [ ] Run unit tests; record result.
- [ ] Commit model and tests.

### Task 2: Branded Android preview

**Files:** `build.gradle`, `settings.gradle`, `gradle.properties`, `app/build.gradle`, `app/src/main/AndroidManifest.xml`, `app/src/main/java/com/innative/senlis/MainActivity.java`, `app/src/main/res/drawable/*`, `app/src/main/res/values/styles.xml`.

**Interfaces:** UI consumes `MatchEngine` and a local seed catalogue; state uses SharedPreferences.

- [ ] Create a native launcher and welcome flow with original photography.
- [ ] Build five preference steps, home/search, detail, favourites, community preview and profile.
- [ ] Verify back navigation, local persistence, labels and small-screen scrolling.
- [ ] Commit UI and assets.

### Task 3: Build and verification

**Files:** `.github/workflows/build-apk.yml`, `README.md`.

- [ ] Add Windows/X64 build job with SDK detection, unit test and APK upload.
- [ ] Run local pure-Java tests and a CI debug build; inspect logs and artifact metadata.
- [ ] Document verified features and the later catalogue/community/notifications phases.
- [ ] Open a draft PR against `main` for review, keeping the empty main branch intact.
