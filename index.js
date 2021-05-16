//javascript
/*
d3.select();
d3.selectAll();

d3.select('h1').style('color', 'red')
.attr('class', 'heading')
.text('Updated h1 tag');

d3.select('body').append('p').text('1st para');
d3.select('body').append('p').text('2nd para');
d3.select('body').append('p').text('3rd para');

d3.selectAll('p').style('color', 'blue');
*/
var dataset = [1, 2, 3, 4, 5];

d3.select('body')
    .selectAll('p')
    .data(dataset)
    .enter()
    .append('p') // appends para for each element
    //.text('D3 is great');
    .text(function(d) {return d;});
    