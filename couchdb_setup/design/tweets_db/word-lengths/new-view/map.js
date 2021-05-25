function (doc) {
  doc.text.split(/\\W+/).forEach(function (word) {
    if (["Adelaide", "Melbourne", "Hobart", "Darwin", "Sydney", "Canberra", "Perth (WA)", "Brisbane"].includes(doc.place.name)) {
      emit([doc.place.name, word.length], 1);
    }
  });
}