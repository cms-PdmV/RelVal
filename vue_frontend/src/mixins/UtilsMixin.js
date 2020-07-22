export const utilsMixin = {

  methods: {
    listLength(list) {
      if (!list) {
        return 0;
      }
      if (typeof(list) === "string") {
        return list.split('\n').filter(Boolean).length;
      }
      return list.length;
    },
    makeCopy(obj) {
      return JSON.parse(JSON.stringify(obj));
    },
    makeDASLink(dataset) {
      return 'https://cmsweb.cern.ch/das/request?view=list&limit=50&instance=prod%2Fglobal&input=dataset%3D' + dataset;
    },
    cleanSplit(str) {
      if (!str || !str.length) {
        return [];
      }
      return str.replace(/,/g, '\n').split('\n').map(function(s) { return s.trim() }).filter(Boolean);
    }
  }
}