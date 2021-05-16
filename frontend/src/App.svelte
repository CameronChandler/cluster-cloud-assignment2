<script lang="ts">  
  import mapboxgl from "mapbox-gl";
  import * as d3 from 'd3';

  import { onMount } from "svelte";

  // var mapboxgl = require('mapbox-gl/dist/mapbox-gl.js');

  let scatter_xattr = ''
  let scatter_yattr  = ''

  function handleSubmit(event) {
    scatter_xattr = selected_x.variable
    scatter_yattr = selected_y.variable
    renderD3(".d3_container", scatter_xattr, scatter_yattr)
  }

  let options = [
		{ id: 1, text: `Income`, variable: 'median_income_by_city'},
		{ id: 2, text: `Unemployment`, variable: 'unemployment_pct_by_city' },
		{ id: 3, text: `Word lengths`, variable: 'word_lengths_by_city' }
	];

	let selected_x;
	let selected_y;

	let answer = '';

  async function renderD3(container, xattr, yattr) {
    let response = await fetch('http://localhost:5000/testdata?xattr=' + xattr + '&yattr=' + yattr + '&tag=city_name');
    let response_json = await response.json();

    // response_json = {'data': ...,
    //                  'x_label'}
    //
    //

    let data = response_json['data'];
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
    d3.select(".svg-container").remove();
    var svg = d3.select(container)
      .append("svg")
        .classed('svg-container', true)
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
      .append("g")
        .classed('g-container', true)
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
            zoom: 3,
            center: [133.88, -23.69],
    });

    const metersToPixelsAtMaxZoom = (meters, latitude) =>
    meters / 0.075 / Math.cos(latitude * Math.PI / 180)

    map.on("load", () => {
      map.addSource("ethnicity", {
        type: "geojson",
        // url: 'http://localhost:5000/mapdata?xattr=' + xattr + '&tag=city_name'
        data: {"type": "Feature",
                "geometry": {
                    "type": "MultiPoint",
                    "coordinates": [[133.88, -23.69], 
                                    [133.88, -22.69], 
                                    [134.88, -23.69], 
                                    [134.88, -22.69]]
                },
                "properties": {
                    "title": "Mapbox DC",
                    "marker-symbol": "monument"
                }
            }

        //type: "vector",
        // https://docs.mapbox.com/mapbox-gl-js/style-spec/sources/#vector
        //url: "mapbox://examples.8fgz4egr",
        // http://localhost:5000/mapdata?xattr=' + xattr + '&tag=city_name'
        // 
      });
      map.addLayer({
        id: "population",
        type: "circle",
        source: "ethnicity",
        //"source-layer": "sf2010",
        paint: {
          // make circles larger as the user zooms from z12 to z22
          "circle-radius": {
            base: 2,
            stops: [
              [0, 0],
              [20, metersToPixelsAtMaxZoom(50000, 20)],
            ],
          },
          // color circles by ethnicity, using a match expression
          // https://docs.mapbox.com/mapbox-gl-js/style-spec/#expressions-match
          "circle-color": "#ff3e00",
          // "circle-color": [
          //   "match",
          //   ["get", "ethnicity"],
          //   "White", "#fbb03b",
          //   "Black", "#223b53",
          //   "Hispanic", "#e55e5e",
          //   "Asian", "#3bb2d0",
          //   /* other */ "#ccc",
          // ],
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
  <h1>Hello World!</h1>
  <p>
    Visit the <a href="https://svelte.dev/tutorial">Svelte tutorial</a> to learn
    how to build Svelte apps.
  </p>

  <form on:submit|preventDefault={handleSubmit}>
    <select bind:value={selected_x} on:change="{() => answer = ''}">
      {#each options as option}
        <option value={option}>
          {option.text}
        </option>
      {/each}
    </select>
    <select bind:value={selected_y} on:change="{() => answer = ''}">
      {#each options as option}
        <option value={option}>
          {option.text}
        </option>
      {/each}
    </select>
    
    <button type=submit>
      Submit
    </button>
  </form>


  <div class="d3_container" />

  <div class="map_container">
      <div id="map"/>
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
