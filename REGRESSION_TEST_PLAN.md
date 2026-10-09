# Playable Patch Pro v11.1 Regression Plan

1. Load a single Unity/Luna HTML and a ZIP-based playable.
2. Confirm source network and store URLs are detected.
3. Convert to AppLovin with default options; verify no Mintegral fallback CTA script is injected.
4. Convert to Mintegral with Auto Detect and fallback CTA enabled.
5. Confirm generated CTA appears only when no native Install / Play Now CTA exists.
6. Test INSTALL, PLAY NOW, and custom CTA labels.
7. Test all four CTA positions and four themes.
8. Test optional CTA image upload; reject images larger than 2 MB.
9. Confirm CTA click calls guarded window.install().
10. With hide-on-end enabled, confirm generated CTA hides on gameEnd or native end-card CTA appearance.
11. Test Manual CSS Selector and Manual Function modes.
12. Verify Mintegral ZIP contains mintegral/mintegral.html and mintegral/mraid.js.
13. Verify uploaded ZIP support files remain preserved.
14. Run strict preflight and inline JavaScript syntax scan.
15. Test mobile-width layout for CTA Builder controls.
