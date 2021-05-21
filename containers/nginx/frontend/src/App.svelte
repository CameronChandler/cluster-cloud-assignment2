<script lang="ts">
  export let name: string;

  import mapboxgl from "mapbox-gl";
  import * as d3 from 'd3';

  import { onMount } from "svelte";

  // var mapboxgl = require('mapbox-gl/dist/mapbox-gl.js');


  let scatter_xattr = ''
  let scatter_yattr  = ''

  function onClick(event) {
    // scatter_xattr = ...
    // scatter_yattr = ...
    // await renderD3(".d3_container", xattr, yattr)
  }

  async function renderD3(container, xattr, yattr) {
    const response = await fetch('/api/testdata?xattr=' + xattr + '&yattr=' + yattr + '&tag=city_name');
    const response_json = await response.json();
    const data = response_json['data'];
    // const data = [
    //   {
    //     tags: {
    //       city_name: "Melbourne"
    //     },
    //     x: 70000,
    //     y: 7,
    //   }
    // ]

    // set the dimensions and margins of the graph
    let margin = {top: 10, right: 30, bottom: 30, left: 60},
        width = 460 - margin.left - margin.right,
        height = 400 - margin.top - margin.bottom;

    // append the svg object to the body of the page
    let svg = d3.select(container)
      .append("svg")
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
      .append("g")
        .attr("transform",
              "translate(" + margin.left + "," + margin.top + ")");

    //Read the data
    function render_data(data) {
      // let max_y = 80000
      let max_y = Math.max(...data.map((city) => {
        return city.y
      }));

      // let max_x = 7.0
      let max_x = Math.max(...data.map((city) => {
        return city.x
      }));

      // Add X axis
      let x = d3.scaleLinear()
        .domain([0, max_x])
        .range([ 0, width ]);
      svg.append("g")
        .attr("transform", "translate(0," + height + ")")
        .call(d3.axisBottom(x));

      // Add Y axis
      let y = d3.scaleLinear()
        .domain([0, max_y])
        .range([ height, 0]);
      svg.append("g")
        .call(d3.axisLeft(y));

      // Add dots
      svg.append('g')
        .selectAll("dot")
        .data(data)
        .enter()
        .append("circle")
          .attr("cx", function (d) { return x(d.x); } )
          .attr("cy", function (d) { return y(d.y); } )
          .attr("r", 1.5)
          .style("fill", "#69b3a2")
    }

    render_data(data)
  }

  mapboxgl.accessToken =
    "pk.eyJ1IjoiYWxhcm9sZGFpIiwiYSI6ImNrb21sMnRwNzBpMzAyb28xaTFjdHMxcHgifQ.DEHbZyOipWRM1qAp3TTQew";
  

  function renderMapbox(container) {
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
        // https://docs.mapbox.com/mapbox-gl-js/style-spec/sources/#vector
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
  }

  onMount(async () => {
    await renderD3(".d3_container", 'unemployment_pct_by_city', 'word_lengths_by_city')
    renderMapbox(".map_container")
  });
</script>

<main>
  <h1>Hello {name}!</h1>
  <p>
    Visit the <a href="https://svelte.dev/tutorial">Svelte tutorial</a> to learn
    how to build Svelte apps.
  </p>

  <button on:click={onClick}>
  </button>



  <div class="d3_container" />

  <div class="map_container">
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

  .map_container {
    display: flex;
    justify-content: center;
  }

  #map {
    width: 75%;
    height: 600px;
  }
</style>
