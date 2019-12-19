// Copyright 2016, University of Freiburg,
// Chair of Algorithms and Data Structures.
// Authors: Patrick Brosi <brosi@informatik.uni-freiburg.de>

#include <glpk.h>
#include <chrono>
#include <cstdio>
#include <fstream>
#include <thread>
#include "transitmap/graph/OrderingConfig.h"
#include "transitmap/optim/CombOptimizer.h"
#include "transitmap/optim/OptGraph.h"
#include "util/String.h"
#include "util/geo/Geo.h"
#include "util/geo/output/GeoGraphJsonOutput.h"
#include "util/graph/Algorithm.h"
#include "util/log/Log.h"

using namespace transitmapper;
using namespace optim;
using namespace transitmapper::graph;
using transitmapper::optim::CombOptimizer;

// _____________________________________________________________________________
int CombOptimizer::optimizeComp(const std::set<OptNode*>& g,
                                HierarchOrderingConfig* hc, size_t depth) const {
  size_t maxC = maxCard(g);
  double solSp = solutionSpaceSize(g);

  LOG(DEBUG) << prefix(depth, 1) << "(CombOptimizer) Optimizing component with " << g.size()
             << " nodes, max cardinality " << maxC << ", solution space size "
             << solSp;

  T_START(optim);

  if (maxC == 1) {
    _nullOpt.optimizeComp(g, hc, depth + 1);
  } else if (solSp < 10) {
    _exhausOpt.optimizeComp(g, hc, depth + 1);
  } else {
    _ilpOpt.optimizeComp(g, hc, depth + 1);
  }

  LOG(DEBUG)  << prefix(depth, 0) << "(CompOptimizer) Done in " << T_STOP(optim) << " ms";

  return 0;
}
