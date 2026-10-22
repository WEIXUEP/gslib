#include "gslib.h"

int main(void)
{
  if(GS_FILE[0] != '\0') return 1;
  diagnostic("", "private/source_file.c", 123, "protection diagnostic");
  return 0;
}
