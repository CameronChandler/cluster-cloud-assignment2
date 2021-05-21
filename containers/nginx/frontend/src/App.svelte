<script lang="ts">  
  import mapboxgl from "mapbox-gl";
  import * as d3 from 'd3';

  import { onMount } from "svelte";

  // var mapboxgl = require('mapbox-gl/dist/mapbox-gl.js');

  let scatter_xattr = ''
  let scatter_yattr  = ''
  let map_attr  = ''

  function handleSubmitChart(event) {
    scatter_xattr = selected_x.variable
    scatter_yattr = selected_y.variable
    renderD3(".d3_container", scatter_xattr, scatter_yattr)
  }

  function handleSubmitMap(event) {
    map_attr = selected_map.variable
    renderMapbox(".map_container", map_attr)
  }

  let options = [
    {id: 1, text: 'Income', variable: 'median_income_by_city'},
    {id: 2, text: 'Unemployment', variable: 'unemployment_pct_by_city'},
    {id: 3, text: 'Higher Education', variable: 'non_school_qualifications_by_city'},
    {id: 4, text: 'Average Word Length', variable: 'word_lengths_by_city'}
  ];

  let selected_x, selected_y, selected_map;
  let default_x = 'median_income_by_city';
  let default_y = 'median_income_by_city';
  let default_map = 'median_income_by_city';

  let answer = '';

  async function renderD3(container, xattr, yattr) {
    let response = await fetch('/testdata?xattr=' + xattr + '&yattr=' + yattr);
    let response_json = await response.json();
    let data = response_json['data'];
    
    let response_x = await fetch('/graphkeys?attr=' + xattr);
    let graphkeys_x = await response_x.json();
    
    let response_y = await fetch('/graphkeys?attr=' + yattr);
    let graphkeys_y = await response_y.json();

    // set the dimensions and margins of the graph
    let margin = {top: 20, right: 30, bottom: 30, left: 60},
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
      let min_x = Math.min(...data.map((city) => {
        return city.x
      }));
      let max_x = Math.max(...data.map((city) => {
        return city.x
      }));
      let min_y = Math.min(...data.map((city) => {
        return city.y
      }));
      let max_y = Math.max(...data.map((city) => {
        return city.y
      }));

      // Add X axis
      let x = d3.scaleLinear()
        .domain([0.9*min_x, 1.1*max_x])
        .range([ 0, width ]);
      svg.append("g")
        .attr("transform", "translate(0," + height + ")")
        .call(d3.axisBottom(x));

      // Add Y axis
      let y = d3.scaleLinear()
        .domain([0.9*min_y, 1.1*max_y])
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
          .attr("r", 5)
          .style("fill", "#ff3e00")

      //Create Title 
      svg.append("text")
      .attr("x", width / 2 )
      .attr("y", 0)
      .style("text-anchor", "middle")
      //.style("font-size", "34px")
      .text(graphkeys_x['text'] + " vs. " + graphkeys_y['text']);

      svg.append("text")
        .attr("class", "x label")
        .attr("text-anchor", "end")
        .attr("x", width)
        .attr("y", height - 6)
        .text(graphkeys_x['label']);

      svg.append("text")
        .attr("class", "y label")
        .attr("text-anchor", "end")
        .attr("y", 6)
        .attr("dy", ".75em")
        .attr("transform", "rotate(-90)")
        .text(graphkeys_y['label']);
    }

    render_data(data)
  }

  mapboxgl.accessToken = "pk.eyJ1IjoiYWxhcm9sZGFpIiwiYSI6ImNrb21sMnRwNzBpMzAyb28xaTFjdHMxcHgifQ.DEHbZyOipWRM1qAp3TTQew";
  
  async function renderMapbox(container, attr) {
    let response = await fetch('/mapdata?xattr=' + attr);
    let response_json = await response.json();

    let data = response_json['data'];
    let geodata = response_json['geodata'];

    var map = new mapboxgl.Map({
      container: "map",
      // style: "mapbox://styles/mapbox/dark-v10",
            style: "mapbox://styles/mapbox/streets-v11",
            zoom: 3,
            center: [133.88, -23.69],
    });

  let min_x = Math.min(...Object.values(data));
  let max_x = Math.max(...Object.values(data));

    map.on("load", () => {
      map.addSource("map_data", geodata);
      // Get feature.properties.x
      const xdata = ['get', 'x']
      map.addLayer({
        id: "map_data",
        type: "circle",
        source: "map_data",
        paint: {"circle-radius": {base: 2, stops: [[0, 0], [20, 1500000],],},
          "circle-color": ['case', 
            ['boolean', ['<', xdata, min_x + (max_x - min_x)*0.2], true], "#ffba08", 
            ['boolean', ['<', xdata, min_x + (max_x - min_x)*0.4], true], "#faa307",
            ['boolean', ['<', xdata, min_x + (max_x - min_x)*0.6], true], "#f48c06", 
            ['boolean', ['<', xdata, min_x + (max_x - min_x)*0.8], true], "#e85d04", "#dc2f02"]
        },
      });

      // Create a popup, but don't add it to the map yet.
      var popup = new mapboxgl.Popup({
        closeButton: false,
        closeOnClick: false
      });
      
      map.on('mouseenter', 'map_data', function (e) {
        // Change the cursor style as a UI indicator.
        map.getCanvas().style.cursor = 'pointer';
        
        var coordinates = e.features[0].geometry.coordinates.slice();
        var description = e.features[0].properties.description;
        
        // Ensure that if the map is zoomed out such that multiple
        // copies of the feature are visible, the popup appears
        // over the copy being pointed to.
        while (Math.abs(e.lngLat.lng - coordinates[0]) > 180) {
          coordinates[0] += e.lngLat.lng > coordinates[0] ? 360 : -360;
        }
        
        // Populate the popup and set its coordinates
        // based on the feature found.
        popup.setLngLat(coordinates).setHTML(description).addTo(map);
      });
      
      map.on('mouseleave', 'map_data', function () {
        map.getCanvas().style.cursor = '';
        popup.remove();
      });
    
    });
  }

  onMount(async () => {
    await renderD3(".d3_container", default_x, default_y)
    await renderMapbox(".map_container", default_map)
  });
</script>

<main>
  <h1>Literacy Analysis</h1>
  <p>
    Choose an x and a y attribute to investigate relationships!
  </p>

  <form on:submit|preventDefault={handleSubmitChart}>
    <select bind:value={selected_x} on:blur="{() => answer = ''}">
      {#each options as option}
        <option value={option}>
          {option.text}
        </option>
      {/each}
    </select>
    <select bind:value={selected_y} on:blur="{() => answer = ''}">
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

  <p>
    Choose an attribute to compare cities!
  </p>

  <form on:submit|preventDefault={handleSubmitMap}>
    <select bind:value={selected_map} on:blur="{() => answer = ''}">
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

  .mapboxgl-popup {
    max-width: 400px;
    font: 12px/20px 'Helvetica Neue', Arial, Helvetica, sans-serif;
  }

</style>
