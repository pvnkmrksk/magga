// Copyright 2016, U  //niversity of Freiburg,
// Chair of Algorithms and Data Structures.
// Authors: Patrick Brosi <brosip@informatik.uni-freiburg.de>

#include <stdint.h>
#include <ostream>
#include "./SvgOutput.h"
#include "../geo/PolyLine.h"

using namespace transitmapper;
using namespace output;


// _____________________________________________________________________________
SvgOutput::SvgOutput(std::ostream* o, double scale)
: _o(o), _w(o, true), _scale(scale) {

}

// _____________________________________________________________________________
void SvgOutput::print(const graph::TransitGraph& outG) {
  std::map<std::string, std::string> params;

  int64_t xOffset = outG.getBoundingBox().min_corner().get<0>();
  int64_t yOffset = outG.getBoundingBox().min_corner().get<1>();


  int64_t width = outG.getBoundingBox().max_corner().get<0>() - xOffset;
  int64_t height = outG.getBoundingBox().max_corner().get<1>() - yOffset;

  width *= _scale;
  height *= _scale;

  params["width"] = std::to_string(width) + "px";
  params["height"] = std::to_string(height) + "px";

  *_o << "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n";
  *_o << "<!DOCTYPE svg PUBLIC \"-//W3C//DTD SVG 1.1//EN\" \"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd\">";

  _w.openTag("svg", params);

  // TODO: output edges

  outputEdges(outG, width, height);
  outputNodes(outG, width, height);


  _w.closeTags();
}

// _____________________________________________________________________________
void SvgOutput::outputNodes(const graph::TransitGraph& outG, double w, double h) {
  int64_t xOffset = outG.getBoundingBox().min_corner().get<0>();
  int64_t yOffset = outG.getBoundingBox().min_corner().get<1>();

  _w.openTag("g");
  for (graph::Node* n : outG.getNodes()) {
    renderNodeConnections(outG, n, w, h);
  }
  _w.closeTag();

  _w.openTag("g");
  for (graph::Node* n : outG.getNodes()) {
    std::map<std::string, std::string> params;
    params["cx"] = std::to_string((n->getPos().get<0>() - xOffset) * _scale);
    params["cy"] = std::to_string(h-(n->getPos().get<1>() - yOffset) * _scale);
    if (n->getStops().size() > 0) {
      params["r"] = "5";
      params["stroke"] = "black";
      params["stroke-width"] = "4";
      params["fill"] = "white";
    } else if (false) {
      params["r"] = "5";
      params["fill"] = "#FF00FF";
    }
    _w.openTag("circle", params);
    _w.closeTag();

    /**
    for (auto& f : n->getMainDirs()) {
      const geo::PolyLine p = f.geom;
      std::stringstream attrs;
      attrs << "fill:none;stroke:red"
        << ";stroke-linecap:round;stroke-opacity:0.5;stroke-width:1";
      printLine(p, attrs.str(), w, h, xOffset, yOffset);
    }
    **/
  }
  _w.closeTag();
}

// _____________________________________________________________________________
void SvgOutput::outputEdges(const graph::TransitGraph& outG, double w, double h) {

  _w.openTag("g");
  for (graph::Node* n : outG.getNodes()) {
    for (graph::Edge* e : n->getAdjListOut()) {
      for (const graph::EdgeTripGeom& g : *e->getEdgeTripGeoms()) {
        renderEdgeTripGeom(outG, g, e, w, h);
      }
    }
  }
  _w.closeTag();
}

// _____________________________________________________________________________
void SvgOutput::renderNodeConnections(const graph::TransitGraph& outG,
    const graph::Node* n, double w, double h) {
  int64_t xOffset = outG.getBoundingBox().min_corner().get<0>();
  int64_t yOffset = outG.getBoundingBox().min_corner().get<1>();
  //
  // for testing, just use one edgefront

  std::set<const gtfs::Route*> processed;
  for (size_t i = 0; i < n->getMainDirs().size(); i++) {
    const graph::NodeFront& nf = n->getMainDirs()[i];
    for (auto e : nf.edges) {
      for (auto& etg : *e->getEdgeTripGeoms()) {
        for (auto& tripOcc : *etg.getTrips()) {
          if (!processed.insert(tripOcc.route).second) continue;
          util::geo::Point p = nf.getTripOccPos(tripOcc.route);
          std::vector<graph::Partner> partners = n->getPartner(&nf, tripOcc.route);

          if (partners.size() == 0) continue;

          util::geo::Point pp = partners[0].front->getTripOccPos(partners[0].route);

          geo::PolyLine line(p, pp);

          std::stringstream attrs;
          attrs << "fill:none;stroke:#" << tripOcc.route->getColorString()
            << ";stroke-linecap:round;stroke-opacity:1;stroke-width:" << etg.getWidth() * _scale;
          printLine(line, attrs.str(), w, h, xOffset, yOffset);
        }
      }
    }
  }

}

// _____________________________________________________________________________
void SvgOutput::renderEdgeTripGeom(const graph::TransitGraph& outG,
    const graph::EdgeTripGeom& g, const graph::Edge* e, double w, double h) {

  const graph::NodeFront* nfTo = e->getTo()->getNodeFrontFor(e);
  const graph::NodeFront* nfFrom = e->getFrom()->getNodeFrontFor(e);

  int64_t xOffset = outG.getBoundingBox().min_corner().get<0>();
  int64_t yOffset = outG.getBoundingBox().min_corner().get<1>();

  geo::PolyLine center = g.getGeom();
  center.simplify(1);
  double lineW = g.getWidth();
  double lineSpc = g.getSpacing();
  double oo = g.getTotalWidth();

  double o = oo;

  for (auto r : g.getTrips()) {
      geo::PolyLine p = center;
      p.offsetPerp(-(o - oo / 2 - g.getWidth() /2));

      // TODO: why is this check necessary? shouldnt be!
      // ___ OUTFACTOR
      if (nfTo->geom.getLine().size() > 0 && nfFrom->geom.getLine().size() > 0) {
        if (g.getGeomDir() == e->getTo()) {
          std::set<geo::PointOnLine, geo::PointOnLineCompare> iSects = nfTo->geom.getIntersections(p);
          if (iSects.size() > 0) {
            p = p.getSegment(0, iSects.begin()->totalPos);
          } else {
            p << nfTo->geom.projectOn(p.getLine().back()).p;
          }

          std::set<geo::PointOnLine, geo::PointOnLineCompare> iSects2 = nfFrom->geom.getIntersections(p);
          if (iSects2.size() > 0) {
            p = p.getSegment(iSects2.begin()->totalPos, 1);
          } else {
            p >> nfFrom->geom.projectOn(p.getLine().front()).p;
          }
        } else {
          p << nfFrom->geom.projectOn(p.getLine().back()).p;
          p >> nfTo->geom.projectOn(p.getLine().front()).p;

          std::set<geo::PointOnLine, geo::PointOnLineCompare> iSects = nfFrom->geom.getIntersections(p);
          if (iSects.size() > 0) {
            p = p.getSegment(0, iSects.begin()->totalPos);
          } else {
            p << nfFrom->geom.projectOn(p.getLine().back()).p;
          }

          std::set<geo::PointOnLine, geo::PointOnLineCompare> iSects2 = nfTo->geom.getIntersections(p);
          if (iSects2.size() > 0) {
            p = p.getSegment(iSects2.begin()->totalPos, 1);
          } else {
            p >> nfTo->geom.projectOn(p.getLine().front()).p;
          }
        }
      }

      // _______ /OUTFACTOR
      std::stringstream attrs;
      attrs << "fill:none;stroke:#" << r.route->getColorString()
        << ";stroke-linecap:round;stroke-opacity:1;stroke-width:" << lineW * _scale;
      printLine(p, attrs.str(), w, h, xOffset, yOffset);
      // break;
      o -= lineW + lineSpc;
  }
}

// _____________________________________________________________________________
void SvgOutput::printPoint(const util::geo::Point& p,
													const std::string& style,
                          double w, double h, int64_t xOffs, int64_t yOffs) {
  std::map<std::string, std::string> params;
  params["cx"] = std::to_string((p.get<0>() - xOffs) * _scale);
  params["cy"] = std::to_string(h-(p.get<1>() - yOffs) * _scale);
  params["r"] = "5";
  params["fill"] = "#FF00FF";
  _w.openTag("circle", params);
  _w.closeTag();
}
// _____________________________________________________________________________
void SvgOutput::printLine(const transitmapper::geo::PolyLine& l,
													const std::string& style,
                          double w, double h, int64_t xOffs, int64_t yOffs) {
	std::map<std::string, std::string> params;
	params["style"] = style;
	std::stringstream points;

	for (auto& p : l.getLine()) {
		points << " " << (p.get<0>() - xOffs)*_scale << "," << h - (p.get<1>() - yOffs) * _scale;
	}

	params["points"] = points.str();

	_w.openTag("polyline", params);
	_w.closeTag();
}