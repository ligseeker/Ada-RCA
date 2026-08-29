# Baseline Experiment Branch

## Branch Identity

- Branch name: `exp/p6-baselines`
- Base branch: `main`
- Base SHA: `bed295326e567395e725caa82840a534dcc0b1de`
- Initialized: 2026-08-29

## Purpose

`exp/p6-baselines` is an isolated external-baseline integration and evaluation
branch. It owns RCAEval integration adapters, non-performance smoke
qualification, compatibility fixes at the adapter boundary, and any later
formally authorized baseline reproduction and evidence artifacts.

This round is limited to P6-E4 Tier-A Baseline Integration Qualification and
the P6-G1 Tier-A Integration Qualification Gate. Formal baseline performance
reproduction is not authorized.

## Scientific Boundary

`main` remains the frozen scientific baseline. The branch does not reopen
Ada-RCA method development and must not modify the frozen Z2 representation,
event-level conditional-logit scorer, lambda, splits, candidate registry, or
the established P3, P4, and P6-G0 conclusions.

External-baseline integration decisions must be based only on source semantics,
dataset schema, provenance, implementation behavior, compatibility, and other
deterministic engineering evidence. Published performance values, root labels,
and performance evaluators must not influence adapter choices or integration
qualification.

## Merge-Back Policy

Baseline development and experiment commits are prohibited on `main`. All
external-baseline work must remain on `exp/p6-baselines` unless a later,
explicitly authorized review approves a controlled merge. This branch must not
be merged into `main` during P6-E4 or P6-G1.
