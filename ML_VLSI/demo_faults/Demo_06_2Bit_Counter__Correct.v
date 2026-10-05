// Correct 2-bit synchronous up counter. On each clock, count increments: 00, 01, 10, 11, 00...
module two_bit_counter_correct (clk, count);
  input clk;
  output [1:0] count;
  wire next_count0, next_count1;

  // Bit 0 toggles every clock; bit 1 toggles whenever bit 0 is 1.
  INV_X1M_A9TH  U1 (.A(count[0]), .Y(next_count0));
  XOR2_X1M_A9TH U2 (.A(count[1]), .B(count[0]), .Y(next_count1));
  DFFQ_X1       U3 (.D(next_count0), .CK(clk), .Q(count[0]));
  DFFQ_X1       U4 (.D(next_count1), .CK(clk), .Q(count[1]));
endmodule
