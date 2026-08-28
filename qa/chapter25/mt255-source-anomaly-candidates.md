# S255 source-anomaly candidates — bounded owner audit

Status: owner-adjudicated; exact unit replay passes
Authority: `authority/fremlin/source/mt2.2016/mt255.tex`, 50,407 bytes,
1,275 lines, SHA-256
`c837735d74f688178acc82b7f004669f2fe3352e5c0293d48442777a9d5bb5b6`

These are the finite, exact candidates from an owner read of the complete
source. Frozen authority bytes remain immutable. Candidates 1–13 and 15 were
confirmed against declarations, types, and the surrounding proof and are
represented by correction rows `O007-CORR-0214`–`O007-CORR-0228`; candidate
12 has two separately ledgered occurrences. Candidate 14 was rejected and the
authority notation was preserved.

1. Line 99: the reverse inequality needed for
   `\mu^*(-A)=\mu^*A` is replaced by the tautology
   `\mu^*A\le\mu^*(-(-A))=\mu^*A`. Expected logic:
   `\mu^*A=\mu^*(-(-A))\le\mu^*(-A)`.
2. Lines 147–148: a null-set calculation in `\BbbR^2` uses the
   one-dimensional measure symbol `\mu` three times where the declared
   two-dimensional measure is `\mu_2`.
3. Line 246: the shear map is cited as `255B(d-e)`, but 255B has only parts
   (a)–(b); the map and inverse are 255A(d)–(e).
4. Line 319: after `f^{\ssbullet}=u`, the second representative is also set
   equal to `u`; it must be `g^{\ssbullet}=v` for `\theta(u,v)`.
5. Line 574: the middle norm begins with a bare absolute-value bar:
   `+|h_x-h_{x'}\|_p`; it needs the norm opener `+\|...`.
6. Line 582: `\|f_x-f_{x'}|_p` has a bare closing bar; it needs
   `\|f_x-f_{x'}\|_p`.
7. Lines 603–608: the `r`-dimensional interval calculation introduces
   `a_n=(\alpha_{n1},\ldots,\alpha_{nr})` but uses undeclared
   `\beta_{ni}` coordinates for `b_n`. The missing coordinate declaration
   for `b_n` must be made explicit.
8. Line 751: `\mu(-(E\cap\ooint{-\pi,\pi})` is missing the closing
   parenthesis around the reflected set.
9. Line 931: the definition of `u*v=w` requires a representative of `v`, but
   the source says `g^{\ssbullet}=w`; it must say `g^{\ssbullet}=v`.
10. Line 933: complex `L^0` is written `L^0(\Bbb C)`, inconsistent with the
    declared and surrounding notation `L^0_{\Bbb C}`.
11. Line 937: active prose repeats `then then`.
12. Lines 987–988 and 992–993: an approximate-identity kernel is required to
    be non-decreasing on both sides of zero. The right-hand condition must be
    non-increasing on `\coint{0,\infty}`; otherwise the stated nonnegative
    integrable shape is not the intended unimodal kernel.
13. Line 1003: the one-sided exponential approximate identity is normalized
    by `1/a`, which has total mass `1/a^2`; the prefactor must be `a` for a
    limit equal to `f(x)` as `a\to\infty`.
14. Line 1028: `a\in\BbbR^r` is tested using scalar notation `|a|`; the
    surrounding vector convention and line 1034 use `\|a\|`.
    **Rejected:** absolute-value bars are an accepted norm notation for vectors
    in this source context; the stylistic difference does not prove an error.
15. Line 1170: the text calls 255A(c)–(d) the two-dimensional results. In
    255A, (a)–(c) are one-dimensional and (d)–(e) are two-dimensional, so the
    exact range must be `255Ad-255Ae`.

Adjudication result: 15 candidates; 14 confirmed groups, one rejected group,
and 15 exact correction rows because the confirmed monotonicity defect occurs
twice. After independent language repairs, the complete target is
`source/id-ID/mt255.tex`, 54,231 bytes, 1,274 logical lines, SHA-256
`29205179dfc0d05c55c2b4b47ad7d72f887a01a5ff55f655f68890b173de23d9`.
The finite structural and normalized-math replay is
`qa/chapter25/mt255-unit-qa.json`; its result is `pass`.
