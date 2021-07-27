// Copyright 2017, University of Freiburg,
// Chair of Algorithms and Data Structures.
// Authors: Patrick Brosi <brosi@informatik.uni-freiburg.de>

#ifndef LOOM_OPTIM_OPTGRAPHSCORER_H_
#define LOOM_OPTIM_OPTGRAPHSCORER_H_

#include <string>
#include <vector>
#include "loom/optim/OptGraph.h"

namespace loom {
namespace optim {

class OptGraphScorer {
 public:
  OptGraphScorer(const Scorer* scorer) : _scorer(scorer) {}

  double getCrossingScore(OptGraph* og, const std::set<OptNode*>& g,
                          const OptOrderCfg& c) const;
  double getCrossingScore(OptGraph* og, OptNode* n, const OptOrderCfg& c) const;

  double getCrossingScore(OptGraph* og, OptEdge* e, const OptOrderCfg& c) const;
  double getSplittingScore(OptGraph* og, OptEdge* e,
                           const OptOrderCfg& c) const;

  double getSplittingScore(OptGraph* og, const std::set<OptNode*>& g,
                           const OptOrderCfg& c) const;
  double getSplittingScore(OptGraph* og, OptNode* n,
                           const OptOrderCfg& c) const;

 private:
  const Scorer* _scorer;

  std::pair<size_t, size_t> getNumCrossings(OptGraph* og, OptNode* n,
                                            const OptOrderCfg& c) const;
  size_t getNumSeparations(OptGraph* og, OptNode* n,
                           const OptOrderCfg& c) const;
};
}  // namespace optim
}  // namespace loom

#endif  // LOOM_OPTIM_OPTGRAPHSCORER_H_