// Copyright 2016, University of Freiburg,
// Chair of Algorithms and Data Structures.
// Authors: Patrick Brosi <brosi@informatik.uni-freiburg.de>

#include "transitmap/graph/Penalties.h"
#include "transitmap/optim/OptGraph.h"
#include "transitmap/optim/OptGraphScorer.h"
#include "transitmap/optim/Optimizer.h"

using namespace transitmapper;
using namespace optim;
using transitmapper::graph::TransitGraph;
using transitmapper::graph::Node;
using transitmapper::graph::Edge;
using transitmapper::graph::Route;
using transitmapper::graph::InnerGeometry;
using transitmapper::graph::IDENTITY_PENALTIES;

// _____________________________________________________________________________
double OptGraphScorer::getSplittingScore(const std::set<OptNode*>& g,
                                         const OptOrderingConfig& c) const {
  double ret = 0;

  for (auto n : g) {
    ret += getSplittingScore(n, c);
  }

  return ret;
}

// _____________________________________________________________________________
double OptGraphScorer::getCrossingScore(const std::set<OptNode*>& g,
                                        const OptOrderingConfig& c) const {
  double ret = 0;

  for (auto n : g) {
    ret += getCrossingScore(n, c);
  }

  return ret;
}

// _____________________________________________________________________________
double OptGraphScorer::getCrossingScore(OptNode* n,
                                        const OptOrderingConfig& c) const {
  if (!n->pl().node) return 0;
  auto numCrossings = getNumCrossings(n, c);

  return numCrossings.first * _scorer->getCrossingPenaltySameSeg(n->pl().node) +
         numCrossings.second * _scorer->getCrossingPenaltyDiffSeg(n->pl().node);
}

// _____________________________________________________________________________
double OptGraphScorer::getSplittingScore(OptNode* n,
                                         const OptOrderingConfig& c) const {
  if (!n->pl().node) return 0;
  return getNumSeparations(n, c) * _scorer->getSplittingPenalty(n->pl().node);
}

// _____________________________________________________________________________
size_t OptGraphScorer::getNumSeparations(OptNode* n,
                                         const OptOrderingConfig& c) const {
  size_t seps = 0;

  for (auto ea : n->getAdjList()) {
    auto linePairs = Optimizer::getLinePairs(ea, true);

    for (auto lp : linePairs) {
      for (auto eb : Optimizer::getEdgePartners(n, ea, lp)) {
        int ainA = std::distance(
            c.at(ea).begin(),
            std::find(c.at(ea).begin(), c.at(ea).end(), lp.first));
        int ainB = std::distance(
            c.at(eb).begin(),
            std::find(c.at(eb).begin(), c.at(eb).end(), lp.first));

        int binA = std::distance(
            c.at(ea).begin(),
            std::find(c.at(ea).begin(), c.at(ea).end(), lp.second));
        int binB = std::distance(
            c.at(eb).begin(),
            std::find(c.at(eb).begin(), c.at(eb).end(), lp.second));

        if (abs(ainA - binA) == 1 && abs(ainB - binB) != 1) {
          seps++;
        }
      }
    }
  }

  return seps;
}

// _____________________________________________________________________________
std::pair<size_t, size_t> OptGraphScorer::getNumCrossings(
    OptNode* n, const OptOrderingConfig& c) const {
  size_t sameSegCrossings = 0;
  size_t diffSegCrossings = 0;

  std::map<LinePair, std::set<OptEdge*>> proced;

  for (auto ea : n->getAdjList()) {
    // line pairs are unique because of the second parameter
    // they are always sorted by their pointer value
    auto linePairs = Optimizer::getLinePairs(ea, true);

    for (auto lp : linePairs) {
      // check if pairs continue in same segments

      // mark this line pair as processed on ea - we have checked it
      // into each adjacent edge
      proced[lp].insert(ea);

      for (auto eb : Optimizer::getEdgePartners(n, ea, lp)) {
        // if we have already fully checked the line pairs on this edge,
        // don't count the crossing again - skip.
        if (proced[lp].count(eb)) continue;

        PosCom posA(std::distance(
                        c.at(ea).begin(),
                        std::find(c.at(ea).begin(), c.at(ea).end(), lp.first)),
                    std::distance(
                        c.at(eb).begin(),
                        std::find(c.at(eb).begin(), c.at(eb).end(), lp.first)));

        PosCom posB(std::distance(
                        c.at(ea).begin(),
                        std::find(c.at(ea).begin(), c.at(ea).end(), lp.second)),
                    std::distance(c.at(eb).begin(),
                                  std::find(c.at(eb).begin(), c.at(eb).end(),
                                            lp.second)));

        PosComPair poses(posA, posB);

        if (Optimizer::crosses(n, ea, eb, poses)) sameSegCrossings++;
      }

      for (auto ebc : Optimizer::getEdgePartnerPairs(n, ea, lp)) {
        PosCom posA(std::distance(
                        c.at(ea).begin(),
                        std::find(c.at(ea).begin(), c.at(ea).end(), lp.first)),
                    std::distance(c.at(ea).begin(),
                                  std::find(c.at(ea).begin(), c.at(ea).end(),
                                            lp.second)));

        if (Optimizer::crosses(n, ea, ebc, posA)) diffSegCrossings++;
      }
    }
  }

  return std::pair<size_t, size_t>(sameSegCrossings, diffSegCrossings);
}

// _____________________________________________________________________________
double OptGraphScorer::getCrossingScore(OptEdge* e,
                                        const OptOrderingConfig& c) const {
  return getCrossingScore(e->getFrom(), c) + getCrossingScore(e->getTo(), c);
}

// _____________________________________________________________________________
double OptGraphScorer::getSplittingScore(OptEdge* e,
                                         const OptOrderingConfig& c) const {
  return getSplittingScore(e->getFrom(), c) + getSplittingScore(e->getTo(), c);
}
