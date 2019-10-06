#!/bin/bash
rm -f Presentation_CFDS.html && jupyter nbconvert --to slides Presentation_CFDS.ipynb \
--post serve \
--SlidesExporter.reveal_scroll=True \
--SlidesExporter.reveal_transition=none  \
--SlidesExporter.reveal_theme=right
