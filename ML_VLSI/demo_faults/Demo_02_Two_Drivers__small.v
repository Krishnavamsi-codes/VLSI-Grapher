// Presentation demo: U1 and U2 both drive shared_net. A normal logic net must have one driver.
module demo_two_drivers (a, b, y);
  input a, b;
  output y;
  wire shared_net;

  NAND2_X1M_A9TH U1 (.A(a), .B(b), .Y(shared_net));
  NOR2_X0P5M_A9TH U2 (.A(a), .B(b), .Y(shared_net));
  INV_X1M_A9TH   U3 (.A(shared_net), .Y(y));
endmodule
