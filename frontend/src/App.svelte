<script lang="ts">
  export let name: string;

  import mapboxgl from "mapbox-gl";

  import { onMount } from "svelte";

  // var mapboxgl = require('mapbox-gl/dist/mapbox-gl.js');

  mapboxgl.accessToken =
    "pk.eyJ1IjoiYWxhcm9sZGFpIiwiYSI6ImNrb21sMnRwNzBpMzAyb28xaTFjdHMxcHgifQ.DEHbZyOipWRM1qAp3TTQew";
  onMount(async () => {
    var map = new mapboxgl.Map({
      container: "map",
      // style: "mapbox://styles/mapbox/dark-v10",
			style: "mapbox://styles/mapbox/streets-v11",
			zoom: 12,
			center: [-122.447303, 37.753574],
    });

    map.on("load", () => {
      map.addSource("ethnicity", {
        type: "vector",
        url: "mapbox://examples.8fgz4egr",
      });
      map.addLayer({
        id: "population",
        type: "circle",
        source: "ethnicity",
        "source-layer": "sf2010",
        paint: {
          // make circles larger as the user zooms from z12 to z22
          "circle-radius": {
            base: 1.75,
            stops: [
              [12, 2],
              [22, 180],
            ],
          },
          // color circles by ethnicity, using a match expression
          // https://docs.mapbox.com/mapbox-gl-js/style-spec/#expressions-match
          "circle-color": [
            "match",
            ["get", "ethnicity"],
            "White", "#fbb03b",
            "Black", "#223b53",
            "Hispanic", "#e55e5e",
            "Asian", "#3bb2d0",
            /* other */ "#ccc",
          ],
        },
      });
    });
  });
</script>

<main>
  <h1>Hello {name}!</h1>
  <p>
    Visit the <a href="https://svelte.dev/tutorial">Svelte tutorial</a> to learn
    how to build Svelte apps.
  </p>

  <div class="container">
    <div id="map" />
  </div>
</main>

<style>
  main {
    text-align: center;
    padding: 1em;
    max-width: 240px;
    margin: 0 auto;
  }

  h1 {
    color: #ff3e00;
    text-transform: uppercase;
    font-size: 4em;
    font-weight: 100;
  }

  @media (min-width: 640px) {
    main {
      max-width: none;
    }
  }

  .container {
    display: flex;
    justify-content: center;
  }

  #map {
    width: 75%;
    height: 600px;
  }
</style>
