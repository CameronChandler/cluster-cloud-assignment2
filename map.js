function (doc) {
    doc.text.split(/\W+/).forEach(function (word) {
          emit([doc.location, word.length], 1);
      });
}