// Copyright 2016, University of Freiburg,
// Chair of Algorithms and Data Structures.
// Authors: Patrick Brosi <brosip@informatik.uni-freiburg.de>

#ifndef TRANSITMAP_UTIL_XMLWRITER_H_
#define TRANSITMAP_UTIL_XMLWRITER_H_

#include <ostream>
#include <string>
#include <stack>
#include <map>

namespace transitmapper {
namespace util {

class XmlWriterException: public std::exception {
 public:
  XmlWriterException(std::string msg)
   : _msg(msg) {}
  ~XmlWriterException() throw() {}

  virtual const char* what() const throw() {
    return _msg.c_str();
  };

 private:
  std::string _msg;
};

// simple XML writer class without much overhead
class XmlWriter {

 public:
  explicit XmlWriter(std::ostream* out);
  XmlWriter(std::ostream* out, bool pretty);
  XmlWriter(std::ostream* out, bool pretty, size_t indent);
  ~XmlWriter() {};

  // open tag without attributes
  void openTag(const std::string& tag);

  // open tag with single attribute (for convenience...)
  void openTag(const std::string& tag,
          const std::string& key, const std::string& val);

  // open tag with attribute list
  void openTag(const std::string& tag,
               const std::map<std::string, std::string>& attrs);

  // open comment
  void openComment();

  // write text
  void writeText(const std::string& text);

  // close tag
  void closeTag();

  // close all open tags, essentially closing the document
  void closeTags();

 private:

  enum XML_NODE_T {
    TAG, TEXT, COMMENT
  };

  struct XmlNode {
    XmlNode(XML_NODE_T t, const std::string& pload, bool hanging)
    : t(t), pload(pload), hanging(hanging) {}
    XML_NODE_T t;
    std::string pload;
    bool hanging;
  };

  std::ostream* _out;
  std::stack<XmlNode> _nstack;

  bool _pretty;
  size_t _indent;

  // handles indentation
  void doIndent();

  // close "hanging" tags
  void closeHanging();

  // pushes XML escaped text to stream
  void putEsced(std::ostream* out, const std::string& str);

  // checks tag names for validiy
  void checkTagName(const std::string& str) const;
};

}}

#endif  // TRANSITMAP_UTIL_XMLWRITER_H_