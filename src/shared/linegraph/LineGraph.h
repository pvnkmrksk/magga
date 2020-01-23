// Copyright 2017, University of Freiburg,
// Chair of Algorithms and Data Structures.
// Authors: Patrick Brosi <brosi@informatik.uni-freiburg.de>

#ifndef SHARED_LINEGRAPH_LINEGRAPH_H_
#define SHARED_LINEGRAPH_LINEGRAPH_H_

#include "shared/linegraph/LineEdgePL.h"
#include "shared/linegraph/LineNodePL.h"
#include "util/geo/Geo.h"
#include "util/geo/Grid.h"
#include "util/graph/UndirGraph.h"

namespace shared {
namespace linegraph {

typedef util::graph::Node<LineNodePL, LineEdgePL> LineNode;
typedef util::graph::Edge<LineNodePL, LineEdgePL> LineEdge;

typedef std::pair<LineEdge*, LineEdge*> LineEdgePair;

typedef util::geo::Grid<LineNode*, util::geo::Point, double> NodeGrid;
typedef util::geo::Grid<LineEdge*, util::geo::Line, double> EdgeGrid;

struct ISect {
  LineEdge *a, *b;
  util::geo::LinePoint<double> bp;
};

class LineGraph
    : public util::graph::UndirGraph<LineNodePL, LineEdgePL> {
 public:
  LineGraph();

  void readFromJson(std::istream* s, double smooth);
  void readFromDot(std::istream* s, double smooth);

  const util::geo::Box<double>& getBBox() const;
  void topologizeIsects();

  size_t maxDeg() const;

  // TODO: make the following functions private
  void addLine(const Line* r);
  const Line* getLine(const std::string& id) const;
  void expandBBox(const util::geo::Point<double>& p);
  //

  size_t getNumNds() const;
  size_t getNumNds(bool topo) const;
  size_t getNumLines() const;

  static LineNode* sharedNode(const LineEdge* a, const LineEdge* b);
  static std::vector<LineOcc> getCtdLinesIn(const Line* r,
                                              const LineNode* dir,
                                              const LineEdge* fromEdge,
                                              const LineEdge* toEdge);

  static std::vector<LineOcc> getCtdLinesIn(const LineEdge* fromEdge,
                                              const LineEdge* toEdge);

  static std::vector<const Line*> getSharedLines(const LineEdge* a,
                                              const LineEdge* b);

  static size_t getLDeg(const LineNode* nd);
  static size_t getMaxLineNum(const LineNode* nd);
  size_t getMaxLineNum();

  static std::vector<Partner> getPartners(const LineNode* n, const NodeFront* f,
                                   const LineOcc& ro);

 private:
  util::geo::Box<double> _bbox;

  ISect getNextIntersection();

  void buildGrids();

  std::set<LineEdge*> proced;
  std::map<std::string, const Line*> _lines;

  NodeGrid _nodeGrid;
  EdgeGrid _edgeGrid;
};

}  // linegraph
}  // shared

#endif  // SHARED_LINEGRAPH_LINEGRAPH_H_