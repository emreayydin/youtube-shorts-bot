"""Automatisch geschriebene, gegen Wikipedia gepruefte Fakten (scripts/faktenbank_nachfuellen.py). Nicht von Hand ordnen."""

NEU = [{'category': 'Astronomie',
  'title': 'Die Sonne besitzt 99,86 % der Masse unseres Systems',
  'hook': 'Fast die gesamte Masse des Sonnensystems steckt in ihr.',
  'body': 'Die Sonne wirkt gigantisch, doch ihr wahrer Anteil am Sonnensystem ist noch '
          'erstaunlicher. Sie vereinigt rund 99,86 Prozent der gesamten Masse des Sonnensystems in '
          'sich. Sämtliche Planeten, Zwergplaneten, Monde, Asteroiden und Kometen machen zusammen '
          'nur mickrige 0,14 Prozent aus. Den allergrößten Teil dieses winzigen Rests nimmt der '
          'Jupiter ein. Die Erde ist im Vergleich zur Masse der Sonne ein absolut verschwindend '
          'kleiner Punkt im All.',
  'cta': 'Hättest du gedacht, dass die Erde im Vergleich so unbedeutend ist?',
  'tags': ['Astronomie', 'Sonne', 'Weltall', 'Sonnensystem', 'Wissen'],
  'sources': ['NASA: Sun Fact Sheet', 'DLR: Die Sonne'],
  'image_prompts': ['Cinematic view of the glowing bright Sun dominating space, realistic space '
                    'imagery, no text',
                    '3D solar system diagram showing tiny planets next to a massive glowing Sun, '
                    'high detail, no text',
                    'Jupiter and gas giants visible as tiny dots in front of the giant Sun '
                    'surface, photorealistic, no text',
                    'Planet Earth tiny in dark space with lens flare from the Sun, ultra high '
                    'resolution, no text']},
 {'category': 'Psychologie',
  'title': 'Dieser Horoskop-Trick täuscht fast jeden',
  'hook': 'Ein Text aus der Zeitung passt angeblich perfekt zu dir.',
  'body': 'Der Psychologe Bertram Forer gab 1948 seinen Studenten einen Persönlichkeitstest. Nach '
          'der Auswertung überreichte er jedem Teilnehmer ein angeblich individuelles '
          'Persönlichkeitsprofil. Auf einer Skala von null bis fünf sollten sie bewerten, wie '
          'treffend die Beschreibung war. Der Durchschnitt lag bei 4,26 Punkten. Das Erstaunliche: '
          'Alle Studenten hatten exakt denselben Text erhalten, den Forer aus Horoskopen '
          'zusammengestellt hatte. Dieses Phänomen nennt man Barnum-Effekt. Menschen neigen dazu, '
          'vage Aussagen über sich selbst als hochpräzise zu empfinden.',
  'cta': 'Glaubst du manchmal an dein Horoskop?',
  'tags': ['Psychologie', 'BarnumEffekt', 'Horoskop', 'Täuschung', 'Experiment'],
  'sources': ['Journal of Abnormal and Social Psychology: The fallacy of personal validation',
              'Britannica: Barnum effect'],
  'image_prompts': ['A vintage 1940s university lecture hall with students reading paper '
                    'documents, sepia tones, realistic, no text',
                    'A printed psychological evaluation sheet lying on an old wooden desk with a '
                    'fountain pen, shallow depth of field, no text',
                    'Astrological symbols and personality traits subtly merging in abstract light, '
                    'elegant concept art, no text',
                    'A close-up of a student thoughtfully reading a document under a desk lamp, '
                    'cinematic, no text']},
 {'category': 'Astronomie',
  'title': 'Uranus rollt seitlich um die Sonne',
  'hook': 'Dieser Planet liegt beim Kreisen komplett auf der Seite.',
  'body': 'Während die meisten Planeten wie ein Kreisel um die Sonne wandern, rollt Uranus '
          'buchstäblich auf seiner Umlaufbahn. Seine Rotationsachse ist um rund 98 Grad gekippt. '
          'Vermutlich kippte eine gewaltige Kollision mit einem Protoplaneten in der Frühzeit des '
          'Sonnensystems den Eisriesen um. Diese extreme Schieflage sorgt für bizarre '
          'Jahreszeiten. Ein Umlauf um die Sonne dauert 84 Erdjahre. Dadurch herrscht an jedem Pol '
          'abwechselnd 42 Jahre lang ununterbrochen Tag und danach 42 Jahre lang völlige '
          'Dunkelheit.',
  'cta': 'Könntest du 42 Jahre Dauernacht aushalten?',
  'tags': ['Uranus', 'Planeten', 'Sonnensystem', 'Weltall', 'Astronomie'],
  'sources': ['NASA: Uranus In Depth', 'ESA: The tilted giant Uranus'],
  'image_prompts': ['Realistic render of Uranus tilted on its side orbiting in space, rings '
                    'visible, dark background, no text',
                    'Diagram-style view of the solar system showing the unusual 98 degree tilt of '
                    'planet Uranus, no text',
                    'Close-up of the pale cyan atmosphere of Uranus with faint rings and distant '
                    'sun, no text',
                    'Artistic depiction of a giant protoplanet colliding with the early planet '
                    'Uranus in deep space, no text']}]
