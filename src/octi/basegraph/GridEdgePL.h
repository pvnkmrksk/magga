// Copyright 2016, University of Freiburg,
// Chair of Algorithms and Data Structures.  // Authors: Patrick Brosi <brosi@informatik.uni-freiburg.de>

#ifndef OCTI_BASEGRAPH_GRIDEDGEPL_H_
#define OCTI_BASEGRAPH_GRIDEDGEPL_H_

#include <set>
#include "octi/combgraph/CombEdgePL.h"
#include "octi/combgraph/CombNodePL.h"
#include "util/geo/GeoGraph.h"
#include "util/geo/PolyLine.h"
#include "util/graph/Node.h"

using util::geo::PolyLine;

namespace octi {
namespace basegraph {

class GridEdgePL : util::geograph::GeoEdgePL<double> {
 public:
  GridEdgePL(double c, bool secondar, bool sink);
  GridEdgePL(double c, bool secondar, bool sink, bool closed);

  const util::geo::Line<double>* getGeom() const;
  util::json::Dict getAttrs() const;

  void setCost(double c);
  double cost() const;
  double rawCost() const;
  bool isSecondary() const;

  void close();
  void open();
  bool closed() const;

  void block();
  void unblock();

  void reset();

  void clearResEdges();
  void addResEdge();

  void setId(size_t id);
  size_t getId() const;

  void setRndrOrder(size_t order);

 private:
  double _c;

  bool _isSecondary;
  bool _isSink;

  bool _closed;

  // edges are blocked if they would cross a settled edge
  bool _blocked;

  uint8_t _resEdgs;
  size_t _rndrOrder;
  size_t _id;
};
}
}

#endif  // OCTI_BASEGRAPH_GRIDEDGEPL_H_
